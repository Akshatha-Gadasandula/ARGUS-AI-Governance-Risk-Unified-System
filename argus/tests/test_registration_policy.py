import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI

from argus.api.routers import registry
from argus.core.registry.service import DuplicateRegistrationError, RegistryService
from argus.core.schemas import AISystemCreate


def test_duplicate_over_http_is_409_before_llm_and_new_version_is_allowed(monkeypatch):
    rows = {}
    class Session:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
        async def execute(self, statement):
            values = statement.compile().params
            existing = rows.get((values["name_1"], values["version_1"]))
            return SimpleNamespace(scalar_one_or_none=lambda: existing)
    session = Session()
    async def sessions():
        yield session
    async def enrich(payload):
        return payload, "Model card"
    registrar = SimpleNamespace(process=AsyncMock(side_effect=enrich))
    classifier = SimpleNamespace(classify=AsyncMock(return_value=SimpleNamespace(overall_risk_tier="MINIMAL_RISK", to_dict=lambda: {})))
    async def save(session, payload, risk, card):
        await RegistryService.ensure_registration_available(session, payload.name, payload.version)
        rows[(payload.name, payload.version)] = "existing-id"
        return SimpleNamespace(**{**payload.model_dump(), "id":"test-id", "system_id":"test-system", "risk_tier":"MINIMAL_RISK", "risk_classification_reasoning":"Test", "regulatory_citations":{}, "model_card":card, "monitoring_enabled":False, "registered_at":datetime.now(), "last_classified_at":datetime.now()})
    monkeypatch.setattr(registry, "registrar_agent", registrar)
    monkeypatch.setattr(registry, "risk_classifier_agent", classifier)
    monkeypatch.setattr(RegistryService, "register_system", save)
    app = FastAPI()
    app.include_router(registry.router, prefix="/registry")
    app.dependency_overrides[registry.get_session] = sessions
    app.dependency_overrides[registry.get_current_user] = lambda: {"username":"test"}
    async def run():
        transport = httpx.ASGITransport(app=app)
        payload = {"name":"Duplicate Test", "purpose":"Classify internal administrative documents", "owner_team":"Test", "version":"1.0.0"}
        async def post():
            response = await transport.handle_async_request(httpx.Request("POST", "http://test/registry/systems", json=payload))
            await response.aread()
            return response
        assert (await post()).status_code == 201
        duplicate = await post()
        assert duplicate.status_code == 409
        assert "explicit new version" in duplicate.json()["detail"]
        assert registrar.process.await_count == classifier.classify.await_count == 1
        payload["version"] = "2.0.0"
        assert (await post()).status_code == 201
        assert registrar.process.await_count == classifier.classify.await_count == 2
    asyncio.run(run())


def test_service_duplicate_guard_cannot_fall_back_to_an_in_memory_duplicate():
    session = SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")), execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: "existing-id")))
    payload = AISystemCreate(name="Existing", purpose="Classify internal administrative documents", owner_team="Test")
    import pytest
    with pytest.raises(DuplicateRegistrationError):
        asyncio.run(RegistryService.register_system(session, payload, {}, "card"))
