"""Synthesize grounded, hallucination-free answers from SQL + RAG context."""
import json
from openai import OpenAI
from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, MODEL
from query.router import route
from query.sql_agent import run_sql_query
from query.rag_agent import retrieve, format_context

client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)

SYSTEM = """You are FleetOS, an intelligent assistant for Sunflower Freight Lines LLC.
Answer the operator question using ONLY the data provided below.
- Be concise, accurate, and specific (include dollar amounts, dates, truck numbers)
- Never hallucinate — if the data does not contain the answer, say so clearly
- Cite document filenames when referencing specific records
- Format numbers with commas and dollar signs where appropriate"""


def answer(question: str) -> dict:
    strategy   = route(question)
    sql_result = None
    rag_chunks = []
    context_parts = []

    if strategy in ("sql", "hybrid"):
        sql_result = run_sql_query(question)
        if sql_result["rows"]:
            context_parts.append(
                f"SQL RESULTS (query: {sql_result['sql']}):\n"
                + json.dumps(sql_result["rows"], indent=2, default=str)
            )
        elif sql_result["error"]:
            context_parts.append(f"SQL ERROR: {sql_result['error']}")

    if strategy in ("rag", "hybrid"):
        rag_chunks = retrieve(question, n_results=5)
        if rag_chunks:
            context_parts.append("RETRIEVED DOCUMENTS:\n" + format_context(rag_chunks))

    # Fallback: if primary strategy returned nothing, try the other
    if not context_parts:
        if strategy == "sql":
            rag_chunks = retrieve(question, n_results=4)
            if rag_chunks:
                context_parts.append("RETRIEVED DOCUMENTS:\n" + format_context(rag_chunks))
        elif strategy == "rag":
            sql_result = run_sql_query(question)
            if sql_result["rows"]:
                context_parts.append("SQL RESULTS:\n" + json.dumps(sql_result["rows"], default=str))

    context = "\n\n".join(context_parts) or "No matching data found in the fleet database."

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": f"Data:\n{context}\n\nQuestion: {question}"}
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    return {
        "question": question,
        "strategy": strategy,
        "answer":   resp.choices[0].message.content.strip(),
        "sql":      sql_result,
        "sources":  list({c["metadata"]["filename"] for c in rag_chunks}),
    }
