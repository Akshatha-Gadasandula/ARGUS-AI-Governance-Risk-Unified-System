#!/usr/bin/env python3
"""Step 5 - Verify Alerts"""
import httpx
import json
import sys

async def main():
    async with httpx.AsyncClient() as client:
        print("STEP 5 - Verify Alerts Endpoint")
        print("-" * 50)
        
        response = await client.get("http://127.0.0.1:8000/api/v1/monitoring/alerts")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            alerts = response.json()
            print(f"Alerts found: {len(alerts)}")
            print(json.dumps(alerts, indent=2, default=str))
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
