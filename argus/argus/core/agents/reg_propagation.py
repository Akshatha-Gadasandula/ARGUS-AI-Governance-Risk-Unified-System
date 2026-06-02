"""
Regulatory Propagation Agent - watches for regulation updates and creates remediation tasks.
Autonomous agent that detects regulatory changes and identifies affected AI systems.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from argus.config import settings
from argus.core.registry.models import AISystem
from argus.core.registry.service import RegistryService

logger = logging.getLogger(__name__)


class RegPropagationAgent:
    """
    Autonomous agent for regulatory update detection and propagation.
    Monitors a directory for regulatory update files and creates remediation tasks.
    """

    def __init__(self, settings_obj=None):
        """
        Initialize Regulatory Propagation Agent.
        
        Args:
            settings_obj: Settings object (defaults to global settings)
        """
        self.settings = settings_obj or settings
        self.client = Anthropic(api_key=self.settings.anthropic_api_key)

    async def watch(
        self,
        update_dir: Path,
        session_factory,
        interval_seconds: int = 60,
    ) -> None:
        """
        Background loop watching for regulatory updates.
        
        Args:
            update_dir: Directory to monitor for .txt update files
            session_factory: AsyncSessionLocal factory
            interval_seconds: Check interval
        """
        logger.info(f"Starting regulatory update watcher on {update_dir}")

        while True:
            try:
                async with session_factory() as session:
                    await self._scan_and_process(update_dir, session)
            except Exception as e:
                logger.error(f"Error in regulatory watcher loop: {e}")

            await asyncio.sleep(interval_seconds)

    async def _scan_and_process(self, update_dir: Path, session: AsyncSession) -> None:
        """
        Scan directory for new updates and process them.
        
        Args:
            update_dir: Directory to scan
            session: Database session
        """
        update_dir = Path(update_dir)
        if not update_dir.exists():
            update_dir.mkdir(parents=True, exist_ok=True)
            return

        # Find unprocessed .txt files
        txt_files = list(update_dir.glob("*.txt"))
        if not txt_files:
            return

        logger.info(f"Found {len(txt_files)} potential updates to process")

        for file_path in txt_files:
            # Skip already processed files
            if file_path.with_suffix(".processed").exists():
                continue

            try:
                task_count = await self.process_file(file_path, session)
                logger.info(f"Processed {file_path.name}: created {task_count} remediation tasks")
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}")

    async def process_file(
        self,
        file_path: Path,
        session: AsyncSession,
    ) -> int:
        """
        Process a single regulatory update file.
        
        Args:
            file_path: Path to update file
            session: Database session
            
        Returns:
            Count of remediation tasks created
        """
        logger.info(f"Processing regulatory update: {file_path}")

        file_path = Path(file_path)
        content = file_path.read_text(encoding="utf-8")

        # Extract structured update info
        update_info = await self._extract_update(content)
        if not update_info:
            logger.warning(f"Could not extract update info from {file_path.name}")
            return 0

        # Save regulatory update to DB
        db_update = await RegistryService.save_regulatory_update(
            session,
            framework=update_info.get("framework", "OTHER"),
            title=update_info.get("title", "Regulatory Update"),
            summary=update_info.get("summary", ""),
            affected_articles=update_info.get("affected_articles", []),
        )

        logger.info(f"Saved regulatory update: {db_update.id}")

        # Find affected systems
        affected_systems = await self._find_affected_systems(session, update_info)
        logger.info(f"Found {len(affected_systems)} affected systems")

        # Create remediation tasks
        task_count = 0
        urgency = update_info.get("urgency", "MEDIUM")

        for system in affected_systems:
            tasks_created = await self._create_tasks(
                session,
                system,
                db_update,
                update_info,
                urgency,
            )
            task_count += tasks_created

        # Mark file as processed
        processed_path = file_path.with_suffix(".processed")
        file_path.rename(processed_path)
        logger.info(f"Marked as processed: {processed_path.name}")

        return task_count

    async def _extract_update(self, content: str) -> Optional[dict]:
        """
        Extract structured update information from unstructured text.
        
        Args:
            content: Raw update text
            
        Returns:
            Dictionary with framework, title, summary, affected_articles, urgency, required_actions
        """
        logger.info("Extracting update information via LLM")

        prompt = f"""Parse this regulatory update and return ONLY valid JSON (no markdown, no code blocks):

{content}

Return JSON with exactly this structure:
{{
  "framework": "EU_AI_ACT | RBI | DPDP | EBA | OTHER",
  "title": "Short descriptive title",
  "summary": "2-3 sentence plain English summary of what changed",
  "affected_articles": ["Article 10", "Annex III"],
  "urgency": "HIGH | MEDIUM | LOW",
  "required_actions": ["Action 1", "Action 2", "Action 3"]
}}"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            response_text = response.content[0].text.strip()

            # Parse JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try extracting from markdown
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    result = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                    result = json.loads(json_str)
                else:
                    raise

            logger.info(f"Extracted update: {result['title']} ({result['framework']})")
            return result

        except Exception as e:
            logger.error(f"Error extracting update: {e}")
            return None

    async def _find_affected_systems(
        self,
        session: AsyncSession,
        update_info: dict,
    ) -> list[AISystem]:
        """
        Identify which AI systems are affected by this regulatory change.
        
        Args:
            session: Database session
            update_info: Update information dictionary
            
        Returns:
            List of affected AISystem instances
        """
        logger.info("Identifying affected systems")

        # Get all active systems
        systems = await RegistryService.list_systems(session)

        if not systems:
            return []

        # Build list for Claude to analyze
        systems_list = [
            f"- {s.name} ({s.system_id}): {s.purpose[:100]}"
            for s in systems
        ]

        prompt = f"""Given this regulatory update summary and list of AI systems, identify which systems 
are affected by this change and would need remediation.

REGULATORY UPDATE:
Framework: {update_info.get('framework')}
Title: {update_info.get('title')}
Summary: {update_info.get('summary')}
Affected Articles: {', '.join(update_info.get('affected_articles', []))}

AI SYSTEMS IN GOVERNANCE:
{chr(10).join(systems_list)}

Return ONLY a JSON array of system_ids that are affected. Example:
["system-a1b2c3", "system-d4e5f6"]

If no systems are affected, return: []"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            response_text = response.content[0].text.strip()

            # Parse JSON array
            try:
                affected_ids = json.loads(response_text)
            except json.JSONDecodeError:
                # Try extracting from markdown
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    affected_ids = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                    affected_ids = json.loads(json_str)
                else:
                    affected_ids = []

            # Map to system objects
            affected_systems = [s for s in systems if s.system_id in affected_ids]
            logger.info(f"Identified {len(affected_systems)} affected systems")

            return affected_systems

        except Exception as e:
            logger.error(f"Error identifying affected systems: {e}")
            return []

    async def _create_tasks(
        self,
        session: AsyncSession,
        system: AISystem,
        regulatory_update,
        update_info: dict,
        urgency: str,
    ) -> int:
        """
        Create remediation tasks for affected system.
        
        Args:
            session: Database session
            system: Affected AISystem
            regulatory_update: RegulatoryUpdate database object
            update_info: Update information dictionary
            urgency: Urgency level (HIGH/MEDIUM/LOW)
            
        Returns:
            Count of tasks created
        """
        logger.info(f"Creating remediation tasks for {system.name}")

        # Calculate due date based on urgency
        urgency_days = {"HIGH": 30, "MEDIUM": 90, "LOW": 180}
        due_date = datetime.utcnow() + timedelta(days=urgency_days.get(urgency, 90))

        required_actions = update_info.get("required_actions", ["Review and assess impact"])
        task_count = 0

        for action in required_actions:
            await RegistryService.create_remediation_task(
                session,
                system_id_uuid=system.id,
                title=f"[{update_info.get('framework')}] {action}",
                description=(
                    f"Required action from regulatory update: {update_info.get('title')}\n\n"
                    f"Summary: {update_info.get('summary')}\n\n"
                    f"Affected articles: {', '.join(update_info.get('affected_articles', []))}"
                ),
                due_date=due_date,
                regulatory_update_id=regulatory_update.id,
                assigned_to=system.owner_team,
            )

            # Also create an alert
            await RegistryService.create_alert(
                session,
                system_id_uuid=system.id,
                alert_data={
                    "alert_type": "REGULATORY_CHANGE",
                    "severity": "WARNING" if urgency == "LOW" else "CRITICAL",
                    "title": f"Regulatory Update: {update_info.get('title')}",
                    "description": f"New regulatory requirement detected. {update_info.get('summary')}",
                    "payload": {
                        "framework": update_info.get("framework"),
                        "articles": update_info.get("affected_articles"),
                    },
                    "regulatory_references": update_info.get("affected_articles"),
                },
            )

            task_count += 1

        logger.info(f"Created {task_count} tasks for {system.name}")
        return task_count
