"""Provider-neutral JSON generation with a process-wide budget and grounding.

Only adapters access credentials; logs contain usage metadata, never prompts,
raw responses, exceptions, or credentials. SDK retries are disabled so every
outbound attempt is counted and throttled here.
"""
import asyncio
import hashlib
import json
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def secret_value(value):
    return value.get_secret_value() if hasattr(value, "get_secret_value") else value or ""


@dataclass
class ProviderResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, model, prompt, schema, system, max_tokens) -> ProviderResponse:
        """One outbound attempt; do not retry in the adapter."""


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, key):
        self._key = key
        self._client = None

    def generate(self, model, prompt, schema, system, max_tokens):
        if self._client is None:
            import httpx
            from anthropic import Anthropic
            # Explicit HTTP client also supports the SDK's older version on httpx 0.28.
            self._client = Anthropic(
                api_key=self._key, max_retries=0, timeout=30,
                http_client=httpx.Client(timeout=30),
            )
        response = self._client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return ProviderResponse(
            "".join(block.text for block in response.content if getattr(block, "type", "text") == "text"),
            response.usage.input_tokens, response.usage.output_tokens,
        )


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, key):
        self._key = key
        self._client = None

    def generate(self, model, prompt, schema, system, max_tokens):
        from google import genai
        from google.genai import types
        if self._client is None:
            self._client = genai.Client(
                api_key=self._key,
                http_options=types.HttpOptions(
                    timeout=30000, retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        response = self._client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system or None, max_output_tokens=max_tokens,
                response_mime_type="application/json", response_schema=schema,
            ),
        )
        usage = response.usage_metadata
        return ProviderResponse(
            response.text or "", getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
        )


class ProcessBudget:
    """Shared by all agents/providers in the process, including retry attempts."""

    def __init__(self, clock=time.monotonic, sleep=time.sleep):
        self.lock = threading.RLock()
        self.calls = 0
        self.last_call = None
        self.clock = clock
        self.sleep = sleep

    def reserve(self, cap, rpm):
        if self.calls >= cap:
            return False
        now = self.clock()
        if self.last_call is not None:
            delay = max(0, self.last_call + 60 / rpm - now)
            if delay:
                self.sleep(delay)
        self.last_call = self.clock()
        self.calls += 1
        return True


PROCESS_BUDGET = ProcessBudget()


def ground_citations(data, chunks):
    """Check provision identities, never references mentioned inside other provisions."""
    articles, annexes = set(), []
    for chunk in chunks:
        meta = chunk.metadata
        kind = meta.get("section_type")
        if kind == "article" and meta.get("article_number") is not None:
            articles.add(str(meta["article_number"]))
        elif kind == "annex" and meta.get("annex_id"):
            annexes.append((meta["annex_id"].upper(), str(meta.get("annex_point") or ""), meta.get("annex_subpoint") or ""))
        elif not kind:
            heading = re.match(r"Article\s+(\d+)(?:\s*[-\n]|\s*$)", chunk.page_content, re.I)
            annex = re.match(r"Annex\s+([IVXLCDM]+)\b", chunk.page_content, re.I)
            if heading:
                articles.add(heading[1])
            if annex:
                annexes.append((annex[1].upper(), "", ""))

    def grounded(value):
        if isinstance(value, dict):
            label = value.get("article") or ""
            if value.get("annex"):
                label += f" Annex {value['annex']}"
            if value.get("point"):
                label += f" point {value['point']}"
        else:
            label = str(value)
        arts = re.findall(r"\bArticle\s+(\d+)\b", label, re.I)
        anns = list(re.finditer(r"\bAnnex\s+([IVXLCDM]+)(?:,?\s+point\s+(\d+)(?:\(([a-z])\))?)?", label, re.I))
        if arts or anns:
            return all(article in articles for article in arts) and all(
                any(a == ann[1].upper() and (not ann[2] or (p == ann[2] and (not ann[3] or s == ann[3].lower())))
                    for a, p, s in annexes)
                for ann in anns
            )
        if label.strip().isdigit():
            return label.strip() in articles
        return False

    needs_review = False

    def walk(value):
        nonlocal needs_review
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key in ("citations", "affected_articles") and isinstance(item, list):
                    kept = [citation for citation in item if grounded(citation)]
                    needs_review |= len(kept) != len(item)
                    result[key] = [walk(citation) for citation in kept]
                elif key == "sources" and isinstance(item, list):
                    kept = [source for source in item if not re.search(r"\b(?:Article|Annex)\s+\w+", source, re.I) or grounded(source)]
                    needs_review |= len(kept) != len(item)
                    result[key] = kept
                else:
                    result[key] = walk(item)
            return result
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, str):
            for reference in re.findall(r"\b(?:Article\s+\d+|Annex\s+[IVXLCDM]+(?:,?\s+point\s+\d+(?:\([a-z]\))?)?)", value, re.I):
                needs_review |= not grounded(reference)
        return value

    return walk(data), needs_review


class LLMService:
    def __init__(self, settings, provider=None, budget=None, cache_dir=None, log_path=None):
        self.settings = settings
        self.budget = budget or PROCESS_BUDGET
        self.cache_dir = Path(cache_dir) if cache_dir is not None else PROJECT_ROOT / ".llm_cache"
        self.log_path = Path(log_path) if log_path is not None else PROJECT_ROOT / "logs" / "llm_usage.jsonl"
        anthropic_key = secret_value(settings.anthropic_api_key)
        gemini_key = secret_value(settings.gemini_api_key)
        self._secrets = [key for key in (anthropic_key, gemini_key) if key]
        selected = settings.llm_provider or ("anthropic" if anthropic_key else "gemini" if gemini_key else "none")
        self.model = settings.claude_model if selected == "anthropic" else settings.gemini_model if selected == "gemini" else None
        if selected != "none" and not self.model:
            raise ValueError(f"Set {'GEMINI_MODEL' if selected == 'gemini' else 'CLAUDE_MODEL'} before using this provider")
        key = anthropic_key if selected == "anthropic" else gemini_key
        self.provider = provider
        if self.provider is None and selected != "none" and key:
            self.provider = AnthropicProvider(key) if selected == "anthropic" else GeminiProvider(key)
        self.name = selected if self.provider else "none"

    def _redact(self, value):
        for secret in self._secrets:
            value = value.replace(secret, "[REDACTED]")
        return value

    def _log(self, status, cache_hit=False, usage=None):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": self.name, "model": self._redact(self.model or "") or None,
            "cache_hit": cache_hit, "status": status,
            "input_tokens": usage.input_tokens if usage else None,
            "output_tokens": usage.output_tokens if usage else None,
        }
        with self.log_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(record) + "\n")

    async def generate_json(self, prompt, schema, fallback, chunks=(), system="", max_tokens=1500):
        return await asyncio.to_thread(self.generate, prompt, schema, fallback, chunks, system, max_tokens)

    def generate(self, prompt, schema: type[BaseModel], fallback, chunks=(), system="", max_tokens=1500):
        def rule_based(reason):
            data = fallback() if callable(fallback) else fallback
            data = json.loads(self._redact(json.dumps(data)))
            data, _ = ground_citations(data, chunks)
            return {**data, "llm_provider": "none", "llm_model": None, "needs_review": True, "fallback_reason": reason}

        source_chunks = [{"text": doc.page_content, "metadata": doc.metadata} for doc in chunks]
        effective_prompt = self._redact(
            system + "\n" + prompt
            + "\nReturn only JSON matching this schema:\n" + json.dumps(schema.model_json_schema(), sort_keys=True)
            + "\nCite only provisions in these retrieved chunks. Omit unsupported citations:\n"
            + json.dumps(source_chunks, sort_keys=True, ensure_ascii=False)
        )
        digest = hashlib.sha256(json.dumps([self.name, self.model, effective_prompt], ensure_ascii=False).encode()).hexdigest()
        cache = self.cache_dir / f"{digest}.json"
        # Serialization prevents simultaneous duplicate calls and shares caps/RPM across agents.
        with self.budget.lock:
            if not self.provider:
                self._log("no_provider")
                return rule_based("no_provider")
            try:
                cached_envelope = json.loads(cache.read_text(encoding="utf-8"))
                cached = schema.model_validate(cached_envelope, strict=True).model_dump()
            except (OSError, ValidationError, json.JSONDecodeError):
                cached = None
            if cached is not None:
                data, review = ground_citations(cached, chunks)
                self._log("cache_hit", True, ProviderResponse("", 0, 0))
                return {**data, "llm_provider": self.name, "llm_model": self.model, "needs_review": review or bool(cached_envelope.get("needs_review"))}
            invalid_retries = quota_retries = 0
            for _ in range(4):
                if not self.budget.reserve(self.settings.llm_max_calls, self.settings.llm_max_rpm):
                    self._log("call_cap")
                    return rule_based("call_cap")
                try:
                    response = self.provider.generate(self.model, effective_prompt, schema, self._redact(system), max_tokens)
                except Exception as error:
                    status = getattr(error, "status_code", None) or getattr(error, "code", None)
                    quota = status == 429 or any(word in str(error).lower() for word in ("quota", "resource_exhausted", "rate limit"))
                    self._log("quota_error" if quota else "provider_error")
                    if quota and quota_retries < 2:
                        self.budget.sleep(2 ** quota_retries)
                        quota_retries += 1
                        continue
                    return rule_based("quota_error" if quota else "provider_error")
                try:
                    data = schema.model_validate_json(self._redact(response.text), strict=True).model_dump()
                except ValidationError:
                    self._log("invalid_json", usage=response)
                    if invalid_retries == 0:
                        invalid_retries += 1
                        effective_prompt += "\nYour previous response was invalid. Return only JSON conforming to the supplied schema."
                        continue
                    return rule_based("invalid_json")
                self._log("ok", usage=response)
                data, review = ground_citations(data, chunks)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                temporary = cache.with_suffix(".tmp")
                temporary.write_text(json.dumps({**data, "llm_provider": self.name, "llm_model": self.model, "needs_review": review}, ensure_ascii=False), encoding="utf-8")
                temporary.replace(cache)
                return {**data, "llm_provider": self.name, "llm_model": self.model, "needs_review": review}
            return rule_based("retry_limit")


_services = {}
_services_lock = threading.Lock()


def get_llm(settings):
    with _services_lock:
        if id(settings) not in _services:
            _services[id(settings)] = LLMService(settings)
        return _services[id(settings)]
