"""Classify operator question as: sql | rag | hybrid using LLaMA-3.1-70B."""
from openai import OpenAI
from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, MODEL

client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)

SYSTEM = """You route fleet operator questions to the right query strategy.
Reply with ONLY one word — no explanation:

  sql    → needs aggregation / lookup from structured data (costs, counts, dates, driver info)
  rag    → needs to retrieve or read a specific document
  hybrid → needs BOTH a database query AND document content

Examples:
  "How much did I spend on truck 62?"                           → sql
  "Show me the insurance card for truck 84"                     → rag
  "What documents do I need to renew the plates for truck 37?"  → hybrid
  "Which trucks are most expensive to maintain?"                → sql
  "Where is the bill of sale for truck 21?"                     → rag
  "When does Roberto Quintero's CDL expire?"                    → sql
  "Find all maintenance records for truck 62"                   → hybrid"""


def route(question: str) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": question}
        ],
        temperature=0.0,
        max_tokens=5,
    )
    ans = resp.choices[0].message.content.strip().lower()
    return ans if ans in ("sql", "rag", "hybrid") else "hybrid"
