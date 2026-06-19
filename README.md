# FleetOS — AI Fleet Document Intelligence

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF6B2B?style=for-the-badge&logo=streamlit&logoColor=white)](https://lone-rangers-genai-dd5zcragxffhxogdcsvbmp.streamlit.app)

**Built by Naga Bindu Kondaveeti** | Team: Lone Rangers | Databricks 32-Hour Hackathon 2026

---

FleetOS turns 197 fleet PDFs for Sunflower Freight Lines LLC into a live, queryable knowledge base. Ask anything in plain English — no SQL needed.

**[https://lone-rangers-genai-dd5zcragxffhxogdcsvbmp.streamlit.app](https://lone-rangers-genai-dd5zcragxffhxogdcsvbmp.streamlit.app)**

---

## What It Does

- **Ingests 197 PDFs** across 9 document types (invoices, CDLs, insurance, titles, registrations, leases)
- **Extracts structured data** — VINs, driver names, expiry dates, amounts, vendors
- **Answers natural language questions** powered by LLaMA 3.1 70B via NVIDIA NIM
- **Alerts on compliance risks** — CDL and insurance expiries tracked automatically

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Pipeline | DuckDB · Medallion Architecture (Bronze → Silver → Gold) |
| Vector Search | ChromaDB · sentence-transformers (all-MiniLM-L6-v2) |
| AI / LLM | NVIDIA NIM · LLaMA 3.1 70B · Hybrid RAG + SQL |
| Dashboard | Streamlit · Plotly |

## Dashboard Pages

| Page | Description |
|------|-------------|
| Fleet Overview | KPIs, maintenance cost charts, spend by category |
| Ask Anything | Natural language Q&A over all 197 documents |
| Document Registry | Searchable table of all ingested PDFs |
| Compliance Alerts | Expiring CDLs and insurance sorted by urgency |

## Key Numbers

- **197 PDFs** ingested · **9 document types** · **20 active trucks**
- **$73K** maintenance spend tracked · **4 compliance alerts** active

---

> See [`problem_statement_7/`](./problem_statement_7/README.md) for full technical documentation, architecture details, and local setup instructions.
