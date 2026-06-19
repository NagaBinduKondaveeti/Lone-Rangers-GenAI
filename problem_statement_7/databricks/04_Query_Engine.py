# Databricks notebook source
# MAGIC %md
# MAGIC # FleetOS — Query Engine (Hybrid SQL + RAG)
# MAGIC Interactive query interface powered by NVIDIA NIM (Llama-3.1-70b)

# COMMAND ----------
# MAGIC %pip install openai chromadb sentence-transformers

# COMMAND ----------
from openai import OpenAI
import json
from chromadb.utils import embedding_functions

NVIDIA_API_KEY  = dbutils.secrets.get("fleet-os", "nvidia_api_key")
MODEL           = "meta/llama-3.1-70b-instruct"
CATALOG         = "fleet_os"

client_ai = OpenAI(
    api_key=NVIDIA_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)

def nim(system, user, max_tokens=1024):
    resp = client_ai.chat.completions.create(
        model=MODEL, max_tokens=max_tokens, temperature=0.0,
        messages=[{"role":"system","content":system},
                  {"role":"user","content":user}]
    )
    return resp.choices[0].message.content.strip()

# Build vector index from silver documents
chroma_client = chromadb.EphemeralClient()
ef = embedding_functions.SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection("fleet_docs", embedding_function=ef)

docs = spark.table(f"{CATALOG}.bronze.raw_documents").collect()
for row in docs[:200]:
    collection.upsert(ids=[row.filename], documents=[row.raw_text[:2000]],
                      metadatas=[{"filename": row.filename}])
print(f"\u2713 Indexed {len(docs)} documents in ChromaDB")

# COMMAND ----------
def fleet_query(question: str) -> str:
    _parts = nim(
        "Reply with exactly one word: sql, rag, or hybrid",
        question, max_tokens=10
    ).lower().split()
    strategy = _parts[0] if _parts and _parts[0] in ("sql","rag","hybrid") else "hybrid"

    context_parts = []

    if strategy in ("sql", "hybrid"):
        sql = nim(
            f"""Generate Spark SQL for {CATALOG} tables.
Tables: silver.documents, gold.truck_summary, gold.monthly_spend, gold.expiring_documents
Return only SQL, no explanation.""",
            question, max_tokens=512
        ).rstrip(";")
        try:
            result = spark.sql(sql)
            context_parts.append(f"SQL: {sql}\nResults:\n{result.toPandas().to_string()}")
        except Exception as e:
            context_parts.append(f"SQL error: {e}")

    if strategy in ("rag", "hybrid"):
        results = collection.query(query_texts=[question], n_results=4)
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            context_parts.append(f"[{meta['filename']}]\n{doc}")

    context = "\n\n---\n\n".join(context_parts) or "No data found."
    return nim(
        "You are FleetOS. Answer using only the data below. No hallucinations.",
        f"Data:\n{context}\n\nQuestion: {question}"
    )

# COMMAND ----------
# Test it
print(fleet_query("Which truck has the highest maintenance cost?"))
