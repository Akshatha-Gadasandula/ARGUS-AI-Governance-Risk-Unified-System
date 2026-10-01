#!/usr/bin/env python3
"""Step 7 - Generate Audit Dossier"""
import httpx
import json
from datetime import datetime

async def main():
    async with httpx.AsyncClient() as client:
        print("STEP 7 - Generate Audit Dossier (PDF Export)")
        print("=" * 60)
        
        system_id = "credit_scoring_model-7dcc97"
        
        payload = {
            "system_id": system_id,
            "include_sections": [
                "system_info",
                "risk_assessment",
                "fairness_metrics",
                "alerts",
                "remediation_plan",
                "regulatory_compliance"
            ]
        }
        
        print(f"System: {system_id}")
        print(f"Generating dossier with sections: {', '.join(payload['include_sections'])}")
        print("-" * 60)
        
        try:
            response = await client.post(
                "http://127.0.0.1:8000/api/v1/audit/generate-dossier",
                json=payload,
                timeout=30
            )
            print(f"Status: {response.status_code}")
            
            if response.status_code in (200, 201):
                result = response.json()
                print(f"Dossier ID: {result.get('id', 'N/A')}")
                print(f"System: {result.get('system_id', 'N/A')}")
                print(f"Generated At: {result.get('generated_at', 'N/A')}")
                print(f"File Path: {result.get('pdf_path', 'N/A')}")
                print(f"Content Hash: {result.get('content_hash', 'N/A')}")
                print(f"\nSummary:\n{json.dumps(result.get('compliance_summary', {}), indent=2)}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
