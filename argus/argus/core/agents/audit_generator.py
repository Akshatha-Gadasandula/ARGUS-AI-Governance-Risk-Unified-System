"""
Audit Generator Agent - produces regulator-ready PDF dossiers on demand in under 30 seconds.
Generates comprehensive compliance documentation for AI systems.
"""
import hashlib
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Template
from sqlalchemy.ext.asyncio import AsyncSession

from argus.config import settings
from argus.core.registry.models import AISystem
from argus.core.registry.service import RegistryService

logger = logging.getLogger(__name__)


# HTML Template for Audit Dossier
AUDIT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARGUS AI Governance Audit Dossier</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: "{{ system.system_id }} | Generated {{ generated_at }} | Page " counter(page);
                font-size: 9pt;
                color: #666;
            }
        }
        
        * {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            color: #333;
            line-height: 1.5;
            margin: 0;
            font-size: 10.5pt;
            overflow: visible;
            word-wrap: break-word;
            white-space: normal;
        }
        
        .cover-page {
            page-break-after: always;
            text-align: center;
            padding: 8cm 0;
        }
        
        .cover-page h1 {
            font-size: 36pt;
            color: #1f3a93;
            margin: 0 0 1cm 0;
        }
        
        .cover-page .system-name {
            font-size: 28pt;
            color: #333;
            margin: 2cm 0;
        }
        
        .cover-page .confidential {
            font-size: 18pt;
            color: #c41e3a;
            font-weight: bold;
            margin: 3cm 0;
        }
        
        .cover-page .meta {
            font-size: 11pt;
            color: #666;
            margin-top: 4cm;
        }
        
        h2 {
            font-size: 18pt;
            color: #1f3a93;
            border-bottom: 3px solid #1f3a93;
            padding-bottom: 8px;
            margin-top: 1.2cm;
            margin-bottom: 0.6cm;
            page-break-after: avoid;
        }
        
        h3 {
            font-size: 14pt;
            color: #2a5cbc;
            margin-top: 0.6cm;
            margin-bottom: 0.3cm;
            page-break-after: avoid;
        }
        
        .system-overview {
            background-color: #f5f5f5;
            padding: 0.6cm;
            margin-bottom: 0.7cm;
            border-left: 5px solid #1f3a93;
            page-break-inside: avoid;
            overflow: visible;
            white-space: normal;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 0.7cm;
            page-break-inside: auto;
        }
        
        th, td {
            padding: 7px 8px;
            text-align: left;
            border: 1px solid #c9d2e3;
            vertical-align: top;
            word-wrap: break-word;
            overflow-wrap: break-word;
            white-space: normal;
        }
        
        th {
            background-color: #1f3a93;
            color: white;
            font-weight: bold;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        .risk-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
            color: white;
            font-size: 11pt;
        }
        
        .risk-PROHIBITED {
            background-color: #8b0000;
        }
        
        .risk-HIGH_RISK {
            background-color: #d9534f;
        }
        
        .risk-LIMITED_RISK {
            background-color: #f0ad4e;
        }
        
        .risk-MINIMAL_RISK {
            background-color: #5cb85c;
        }
        
        .risk-UNCLASSIFIED {
            background-color: #5bc0de;
        }
        
        .severity-CRITICAL {
            background-color: #c41e3a;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 10pt;
            font-weight: bold;
        }
        
        .severity-WARNING {
            background-color: #f0ad4e;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 10pt;
            font-weight: bold;
        }
        
        .severity-INFO {
            background-color: #5bc0de;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 10pt;
            font-weight: bold;
        }
        
        .compliance-checklist {
            list-style-type: none;
            padding: 0;
            margin-bottom: 1cm;
        }
        
        .compliance-checklist li {
            padding: 6px 0;
            padding-left: 24px;
            position: relative;
        }
        
        .compliance-checklist li:before {
            content: "✓";
            position: absolute;
            left: 0;
            font-weight: bold;
            color: #5cb85c;
            font-size: 14pt;
        }
        
        .compliance-checklist li.not-compliant:before {
            content: "✗";
            color: #c41e3a;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1cm;
            margin-bottom: 1cm;
        }
        
        .metric-box {
            background-color: #f5f5f5;
            padding: 0.8cm;
            border-radius: 4px;
        }
        
        .metric-box .label {
            font-size: 10pt;
            color: #666;
            margin-bottom: 4px;
        }
        
        .metric-box .value {
            font-size: 18pt;
            font-weight: bold;
            color: #333;
        }
        
        .critical-row {
            background-color: #ffe6e6 !important;
        }
        
        .alert-row {
            background-color: #fff5e6 !important;
        }
        
        .page-break {
            page-break-after: always;
            margin-top: 0.4cm;
        }
        
        blockquote {
            border-left: 4px solid #ddd;
            margin: 1cm 0;
            padding-left: 1cm;
            color: #666;
            font-style: italic;
        }
        
        .footer-note {
            font-size: 9pt;
            color: #999;
            margin-top: 1.2cm;
            padding-top: 0.5cm;
            border-top: 1px solid #ddd;
            page-break-inside: avoid;
            overflow: visible;
            white-space: normal;
        }
    </style>
</head>
<body>
    <!-- COVER PAGE -->
    <div class="cover-page">
        <h1>ARGUS</h1>
        <p style="font-size: 14pt; color: #666;">AI Governance Platform</p>
        <div class="system-name">{{ system.name }}</div>
        <div class="confidential">CONFIDENTIAL — INTERNAL USE ONLY</div>
        <div class="cover-page .meta">
            <p><strong>Generated:</strong> {{ generated_at }}</p>
            <p><strong>By:</strong> {{ generated_by }}</p>
            <p><strong>Source HTML Hash:</strong> {{ content_hash[:16] }}...</p>
            <p><strong>System ID:</strong> {{ system.system_id }}</p>
        </div>
    </div>

    <!-- EXECUTIVE SUMMARY -->
    <h2>Executive Summary</h2>
    <div class="system-overview">
        <p style="margin: 0 0 0.35cm 0; overflow: visible; white-space: normal; word-wrap: break-word;"><strong>What this report covers:</strong> {{ system.name }} is monitored in {{ system.jurisdictions | join(', ') }}.</p>
        <p style="margin: 0 0 0.35cm 0; overflow: visible; white-space: normal; word-wrap: break-word;"><strong>Plain-language risk note:</strong> {{ risk_plain }}</p>
        <p style="margin: 0 0 0.35cm 0; overflow: visible; white-space: normal; word-wrap: break-word;"><strong>Current status:</strong> {{ alert_plain }} {{ fairness_plain }} {{ remediation_plain }}</p>
        <p style="margin: 0; overflow: visible; white-space: normal; word-wrap: break-word;"><strong>What to do next:</strong> Review the open alerts, confirm the assigned owners, and verify whether any fairness or drift issues still need action.</p>
    </div>
    
    <!-- SECTION 1: SYSTEM OVERVIEW -->
    <h2>1. System Overview</h2>
    <p>This section gives the basic facts about the system in a simple format.</p>
    
    <table>
        <tr>
            <th>Property</th>
            <th>Value</th>
        </tr>
        <tr>
            <td><strong>System ID</strong></td>
            <td><code>{{ system.system_id }}</code></td>
        </tr>
        <tr>
            <td><strong>Name</strong></td>
            <td>{{ system.name }}</td>
        </tr>
        <tr>
            <td><strong>Version</strong></td>
            <td>{{ system.version }}</td>
        </tr>
        <tr>
            <td><strong>Owner Team</strong></td>
            <td>{{ system.owner_team }}</td>
        </tr>
        <tr>
            <td><strong>Owner Email</strong></td>
            <td>{{ safe_text(system.owner_email) or 'Not specified' }}</td>
        </tr>
        <tr>
            <td><strong>Registered</strong></td>
            <td>{{ format_optional_datetime(system.registered_at) }}</td>
        </tr>
        <tr>
            <td><strong>Monitoring Status</strong></td>
            <td>{% if system.monitoring_enabled %}✓ Enabled{% else %}✗ Disabled{% endif %}</td>
        </tr>
    </table>
    
    <div class="system-overview">
        <h3>Purpose</h3>
        <p>{{ safe_text(system.purpose) }}</p>
    </div>
    
    <h3>Data Sources</h3>
    {% if system.data_sources %}
        <ul>{% for source in system.data_sources %}<li>{{ safe_text(source) }}</li>{% endfor %}</ul>
    {% else %}
        <p>Not specified</p>
    {% endif %}
    
    <h3>Affected Demographics</h3>
    {% if system.affected_demographics %}
        <ul>{% for demo in system.affected_demographics %}<li>{{ safe_text(demo) }}</li>{% endfor %}</ul>
    {% else %}
        <p>Not specified</p>
    {% endif %}
    
    <h3>Jurisdictions</h3>
    <p>{% for jurisdiction in system.jurisdictions %}
        <span style="background-color: #e8f4f8; padding: 2px 6px; border-radius: 3px; margin-right: 4px;">{{ safe_text(jurisdiction) }}</span>
    {% endfor %}</p>
    
    <div class="page-break"></div>
    
    <!-- SECTION 2: RISK CLASSIFICATION -->
    <h2>2. Risk Classification</h2>
    <p>This section explains why the system is classified this way and what that means operationally.</p>
    
    <div style="text-align: center; margin: 1cm 0;">
        <p style="font-size: 11pt; color: #666; margin-bottom: 0.5cm;">Current Risk Tier:</p>
        <div class="risk-badge risk-{{ display_value(system.risk_tier) }}">{{ display_value(system.risk_tier) }}</div>
    </div>

    <p style="margin: 0 0 0.35cm 0; overflow: visible; white-space: normal; word-wrap: break-word;"><strong>In plain language:</strong> {{ risk_plain }}</p>
    
    {% if system.risk_classification_reasoning %}
    <h3>Classification Reasoning</h3>
    <blockquote>{{ system.risk_classification_reasoning }}</blockquote>
    {% endif %}
    
    {% if system.regulatory_citations %}
    <h3>Regulatory Obligations</h3>
    
    {% for framework, data in system.regulatory_citations.items() %}
    <h4>{{ framework }}</h4>
    
    <h5>Citations</h5>
    {% if data.citations %}
    <table>
        <tr>
            <th>Article</th>
            <th>Title</th>
            <th>Excerpt</th>
        </tr>
        {% for citation in data.citations %}
        <tr>
            <td><code>{{ safe_text(citation.canonical_citation or citation.article) }}</code></td>
            <td>{{ safe_text(citation.title) }}</td>
            <td>{{ safe_text(citation.excerpt)[:100] }}...</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    
    <h5>Required Obligations</h5>
    {% if data.obligations %}
    <ol>
        {% for obligation in data.obligations %}
        <li>{{ obligation }}</li>
        {% endfor %}
    </ol>
    {% endif %}
    {% endfor %}
    {% endif %}
    
    <div class="page-break"></div>
    
    <!-- SECTION 3: FAIRNESS & DRIFT HISTORY -->
    <h2>3. Fairness & Drift Monitoring History</h2>
    <p>This section shows whether recent monitoring results stayed inside policy limits.</p>
    
    {% if fairness_snapshots %}
    <table>
        <tr>
            <th>Date</th>
            <th>Sample Size</th>
            <th>Demographic Parity</th>
            <th>Equalized Odds</th>
            <th>PSI</th>
            <th>Status</th>
        </tr>
        {% for snapshot in fairness_snapshots[:10] %}
        <tr {% if snapshot.demographic_parity_diff > 0.10 or snapshot.equalized_odds_diff > 0.10 or snapshot.psi_score > 0.25 %}class="critical-row"{% elif snapshot.demographic_parity_diff > 0.05 or snapshot.equalized_odds_diff > 0.05 %}class="alert-row"{% endif %}>
            <td>{{ format_optional_datetime(snapshot.evaluated_at) }}</td>
            <td>{{ snapshot.sample_size }}</td>
            <td>{{ "%.4f" | format(snapshot.demographic_parity_diff) }}</td>
            <td>{{ "%.4f" | format(snapshot.equalized_odds_diff) }}</td>
            <td>{{ "%.4f" | format(snapshot.psi_score or 0) }}</td>
            <td>{% if snapshot.demographic_parity_diff > 0.10 %}<span class="severity-CRITICAL">CRITICAL</span>{% elif snapshot.demographic_parity_diff > 0.05 %}<span class="severity-WARNING">WARNING</span>{% else %}<span class="severity-INFO">OK</span>{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p><em>No monitoring data available yet. System monitoring may not be enabled.</em></p>
    {% endif %}
    
    <div class="page-break"></div>
    
    <!-- SECTION 4: GOVERNANCE ALERTS -->
    <h2>4. Governance Alerts</h2>
    <p>This section lists the open governance issues that still need attention.</p>
    
    {% if alerts %}
    <table>
        <tr>
            <th>Date</th>
            <th>Severity</th>
            <th>Type</th>
            <th>Title</th>
            <th>Status</th>
        </tr>
        {% for alert in alerts[:20] %}
        <tr {% if alert.severity == 'CRITICAL' %}class="critical-row"{% elif alert.severity == 'WARNING' %}class="alert-row"{% endif %}>
            <td>{{ format_optional_datetime(alert.created_at) }}</td>
            <td><span class="severity-{{ display_value(alert.severity) }}">{{ display_value(alert.severity) }}</span></td>
                <td>{{ display_value(alert.alert_type) }}</td>
            <td>{{ alert.title }}</td>
            <td>{% if alert.resolved %}✓ Resolved{% else %}⏳ Open{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p><em>No alerts recorded for this system.</em></p>
    {% endif %}
    
    <div class="page-break"></div>
    
    <!-- SECTION 5: REMEDIATION TASKS -->
    <h2>5. Open Remediation Tasks</h2>
    <p>This section shows the work already assigned to fix open issues.</p>
    
    {% if remediation_tasks %}
    <table>
        <tr>
            <th>Task</th>
            <th>Assigned To</th>
            <th>Due Date</th>
            <th>Status</th>
        </tr>
        {% for task in remediation_tasks %}
        <tr>
            <td>{{ task.title }}</td>
            <td>{{ task.assigned_to or 'Unassigned' }}</td>
            <td>{{ format_optional_datetime(task.due_date, '%Y-%m-%d') if task.due_date else 'No deadline' }}</td>
            <td>{{ display_value(task.status) }}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p><em>No open remediation tasks.</em></p>
    {% endif %}
    
    <div class="page-break"></div>
    
    <!-- SECTION 6: AUDIT TRAIL -->
    <h2>6. Audit Trail & Metadata</h2>
    <p>This section records when the report was created and how it can be traced later.</p>
    
    <table>
        <tr>
            <th>Property</th>
            <th>Value</th>
        </tr>
        <tr>
            <td><strong>Generated At</strong></td>
            <td>{{ generated_at }}</td>
        </tr>
        <tr>
            <td><strong>Generated By</strong></td>
            <td>{{ generated_by }}</td>
        </tr>
        <tr>
            <td><strong>Source HTML Hash (SHA-256, before hash insertion)</strong></td>
            <td><code style="font-size: 9pt; word-break: break-all;">{{ content_hash }}</code></td>
        </tr>
        <tr>
            <td><strong>ARGUS Version</strong></td>
            <td>1.0.0</td>
        </tr>
        <tr>
            <td><strong>Frameworks Evaluated</strong></td>
            <td>{% for jurisdiction in system.jurisdictions %}{{ jurisdiction }}{% if not loop.last %}, {% endif %}{% endfor %}</td>
        </tr>
    </table>
    
    <div class="footer-note">
        <p><strong>ARGUS Audit Dossier</strong> — This document is confidential and intended for internal governance and regulatory compliance purposes only. Unauthorized distribution is prohibited.</p>
        <p>Generated by ARGUS AI Governance Platform. For questions, contact the AI Governance team.</p>
    </div>
</body>
</html>"""


class AuditGeneratorAgent:
    """
    Autonomous agent for generating audit dossiers in PDF format.
    Produces comprehensive compliance documentation in under 30 seconds.
    """

    def __init__(self, settings_obj=None):
        """
        Initialize Audit Generator Agent.
        
        Args:
            settings_obj: Settings object (defaults to global settings)
        """
        self.settings = settings_obj or settings
        self.output_dir = Path(self.settings.audit_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        session: AsyncSession,
        system_id: str,
        requested_by: str = "system",
    ):
        """
        Generate audit dossier PDF for a system.
        
        Args:
            session: Database session
            system_id: System ID to audit
            requested_by: User/system requesting audit
            
        Returns:
            Generated AuditRecord
        """
        logger.info(f"Generating audit dossier for {system_id}")

        # Get system data
        audit_data = await RegistryService.get_system_for_audit(session, system_id)
        if not audit_data or "system" not in audit_data:
            logger.error(f"System not found for audit: {system_id}")
            return None

        system: AISystem = audit_data["system"]
        snapshots = audit_data.get("fairness_snapshots", [])
        alerts = audit_data.get("alerts", [])
        remediation_tasks = audit_data.get("remediation_tasks", [])

        # Build template context
        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        def display_value(value):
            return getattr(value, "value", value)

        risk_tier = display_value(system.risk_tier)
        alert_count = len(alerts)
        open_alert_count = len([a for a in alerts if not a.resolved])
        fairness_flag_count = len(
            [
                snapshot
                for snapshot in snapshots
                if snapshot.demographic_parity_diff > 0.05
                or snapshot.equalized_odds_diff > 0.05
                or (snapshot.psi_score or 0) > 0.25
            ]
        )

        if risk_tier == "HIGH_RISK":
            risk_plain = (
                "This system can affect access to credit, so it needs stronger oversight, \
                closer monitoring, and clear documentation."
            )
        elif risk_tier == "LIMITED_RISK":
            risk_plain = "This system has some governance requirements, but the controls are lighter than for high-risk systems."
        elif risk_tier == "MINIMAL_RISK":
            risk_plain = "This system has low governance burden, with routine oversight and documentation."
        else:
            risk_plain = "This system has not been fully classified yet."

        def format_optional_datetime(value, fmt="%Y-%m-%d %H:%M"):
            if not value:
                return "Not available"
            if isinstance(value, str):
                return value
            try:
                return value.strftime(fmt)
            except Exception:
                return str(value)

        def safe_text(value):
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            return str(value)

        if open_alert_count:
            alert_plain = f"There are {open_alert_count} open alerts that need review."
        else:
            alert_plain = "There are no open alerts at the moment."

        if fairness_flag_count:
            fairness_plain = (
                f"Recent monitoring found {fairness_flag_count} fairness or drift checks above the configured threshold."
            )
        else:
            fairness_plain = "Recent monitoring does not show active fairness or drift concerns."

        if remediation_tasks:
            remediation_plain = f"There are {len(remediation_tasks)} remediation tasks in progress."
        else:
            remediation_plain = "There are no open remediation tasks."

        context = {
            "system": system,
            "fairness_snapshots": snapshots,
            "alerts": alerts,
            "remediation_tasks": remediation_tasks,
            "generated_at": generated_at,
            "generated_by": requested_by,
            "content_hash": "placeholder",  # Will be computed after HTML generation
            "display_value": display_value,
            "format_optional_datetime": format_optional_datetime,
            "safe_text": safe_text,
            "risk_tier": risk_tier,
            "alert_count": alert_count,
            "open_alert_count": open_alert_count,
            "fairness_flag_count": fairness_flag_count,
            "risk_plain": risk_plain,
            "alert_plain": alert_plain,
            "fairness_plain": fairness_plain,
            "remediation_plain": remediation_plain,
        }

        try:
            # Render template
            template = Template(AUDIT_TEMPLATE)
            html_content = template.render(**context)

            # Compute content hash before final rendering
            html_bytes = html_content.encode("utf-8")
            content_hash = hashlib.sha256(html_bytes).hexdigest()

            # Re-render with actual hash
            context["content_hash"] = content_hash
            html_content = template.render(**context)

            # Convert to PDF using WeasyPrint (lazy import to avoid system dependency at module import)
            logger.info("Converting HTML to PDF...")
            try:
                from weasyprint import HTML
            except Exception as ie:
                logger.error("WeasyPrint not available or missing system dependencies: %s", ie)
                raise

            try:
                html_obj = HTML(string=html_content)
            except TypeError:
                html_obj = HTML(html_content)

            pdf_bytes = html_obj.write_pdf()

            # Save PDF
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"{system_id}_{timestamp}.pdf"
            pdf_path = self.output_dir / pdf_filename

            pdf_path.write_bytes(pdf_bytes)
            logger.info(f"Saved PDF to {pdf_path}")

            # Compute PDF hash
            pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

            # Save audit record to DB
            record = await RegistryService.save_audit_record(
                session,
                system_id_uuid=system.id,
                pdf_path=str(pdf_path),
                content_hash=pdf_hash,
                summary={
                    "risk_tier": system.risk_tier,
                    "monitoring_enabled": system.monitoring_enabled,
                    "fairness_snapshots_count": len(snapshots),
                    "open_alerts": len([a for a in alerts if not a.resolved]),
                    "open_tasks": len(
                        [t for t in remediation_tasks if t.status.value in ["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]]
                    ),
                },
                generated_by=requested_by,
            )

            logger.info(f"Audit dossier generated successfully for {system_id}")
            return record

        except Exception as e:
            logger.error(f"Error generating audit dossier: {e}")
            raise
