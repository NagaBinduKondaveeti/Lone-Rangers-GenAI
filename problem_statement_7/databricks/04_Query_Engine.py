# Databricks notebook source
# MAGIC %md
# MAGIC # FleetOS — Query Engine (Hybrid SQL + RAG)
# MAGIC Interactive query interface for Databricks

# COMMAND ----------
# MAGIC %pip install anthropic chromadb sentence-transformers

# COMMAND ----------
import anthropic, json
from chromadb import Client
from chromadb.utils import embedding_functions

ANTHROPIC_API_KEY = dbutils.secrets.get("fleet-os", "anthropic_api_key")
MODEL = "claude-sonnet-4-6"
CATALOG = "fleet_os"

client_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Build vector index from silver documents
chroma_client = Client()
ef = embedding_functions.SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection("fleet_docs", embedding_function=ef)

docs = spark.table(f"{CATALOG}.bronze.raw_documents").collect()
for row in docs[:200]:
    collection.upsert(ids=[row.filename], documents=[row.raw_text[:2000]],
                      metadatas=[{"filename": row.filename}])
print(f"✓ Indexed {len(docs)} documents in ChromaDB")

# COMMAND ----------
def fleet_query(question: str) -> str:
    # Route
    route_msg = client_ai.messages.create(
        model=MODEL, max_tokens=10,
        system="Reply with exactly one word: sql, rag, or hybrid",
        messages=[{"role":"user","content": question}]
    )
    strategy = route_msg.content[0].text.strip().lower()

    context_parts = []

    if strategy in ("sql", "hybrid"):
        sql_msg = client_ai.messages.create(
            model=MODEL, max_tokens=512,
            system=f"""Generate DuckDB/Spark SQL for fleet_os.silver.documents and gold tables.
Tables: silver.documents, gold.truck_summary, gold.monthly_spend, gold.expiring_documents
Return only SQL.""",
            messages=[{"role":"user","content": question}]
        )
        sql = sql_msg.content[0].text.strip().rstrip(";")
        try:
            result = spark.sql(sql.replace("silver_documents", f"{CATALOG}.silver.documents")
                               .replace("gold_truck_summary", f"{CATALOG}.gold.truck_summary"))
            context_parts.append(f"SQL: {sql}\nResults:\n{result.toPandas().to_string()}")
        except Exception as e:
            context_parts.append(f"SQL error: {e}")

    if strategy in ("rag", "hybrid"):
        results = collection.query(query_texts=[question], n_results=4)
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            context_parts.append(f"[{meta['filename']}]\n{doc}")

    context = "\n\n---\n\n".join(context_parts) or "No data found."
    answer = client_ai.messages.create(
        model=MODEL, max_tokens=1024,
        system="You are FleetOS. Answer using only the data below. No hallucinations.",
        messages=[{"role":"user","content": f"Data:\n{context}\n\nQuestion: {question}"}]
    )
    return answer.content[0].text.strip()

# COMMAND ----------
# Test it
question = "Which truck has the highest maintenance cost?"
print(fleet_query(question))
