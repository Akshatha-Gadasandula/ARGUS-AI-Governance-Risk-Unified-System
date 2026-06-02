#!/usr/bin/env python3
"""Step 6 - Q&A Questions"""
import httpx
import json
import sys

async def main():
    async with httpx.AsyncClient() as client:
        print("STEP 6 - Run Q&A Questions")
        print("=" * 60)
        
        questions = [
            "What are the critical fairness violations detected in the credit scoring system?",
            "Can you explain the demographic parity difference metric and its significance?",
            "What regulatory framework should guide remediation of bias in AI models?"
        ]
        
        system_id = "credit_scoring_model-7dcc97"
        
        for i, question in enumerate(questions, 1):
            print(f"\nQuestion {i}: {question}")
            print("-" * 60)
            
            payload = {
                "system_id": system_id,
                "question": question
            }
            
            try:
                response = await client.post(
                    "http://127.0.0.1:8000/api/v1/qa/ask",
                    json=payload,
                    timeout=30
                )
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Answer: {result.get('answer', 'No answer')}")
                    print(f"Sources: {result.get('sources', [])}")
                    print(f"Confidence: {result.get('confidence', 'N/A')}")
                else:
                    print(f"Error: {response.text}")
            except Exception as e:
                print(f"Exception: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
