# FleetOS — AI-Powered Fleet Document Intelligence

> **Hackathon Project | Data Pipeline Track | Databricks**
>
> Sunflower Freight Lines LLC has 197 fleet documents buried in filing cabinets and email threads — nothing searchable, nothing linked. FleetOS turns that chaos into a living, queryable knowledge base operators can ask questions in plain English.

---

## The Problem

A trucking company with a growing fleet generates hundreds of documents per year:

- Maintenance invoices from 6+ vendors
- CDL licenses that expire (and legal violations if missed)
- Insurance cards, IRP registrations, vehicle titles
- IRS Form 2290 (Heavy Vehicle Use Tax), IFTA fuel tax returns
- Equipment lease agreements

**None of it was connected.** Finding "when does Driver Omar Haddad's CDL expire?" meant digging through filing cabinets. Finding "which truck costs us the most in maintenance?" was impossible without a spreadsheet.

---

## The Solution

FleetOS ingests every document, links it to the right truck/driver/trailer, and lets operators ask anything in plain English — no SQL knowledge required.

```
197 PDFs  →  Bronze (raw text)  →  Silver (structured entities)  →  Gold (analytics views)
                                                                          ↓
                                                              Natural Language Q&A
```

---

## Architecture

### Medallion Pipeline (Local + Databricks)

| Layer | What it stores | Technology |
|-------|---------------|------------|
| **Bronze** | Raw extracted PDF text | DuckDB / Delta Lake |
| **Silver** | Structured entities (VINs, dates, amounts, drivers) | DuckDB / Delta Lake |
| **Gold** | Aggregated views for dashboards | DuckDB views / Spark SQL |

### Hybrid RAG + SQL Query Engine

Every question is automatically routed to the right strategy:

```
User Question
     │
     ▼
  Router (LLM)
     │
     ├──► SQL     → "Which truck costs the most?" → DuckDB → answer
     ├──► RAG     → "What does the lease agreement say?" → ChromaDB → answer
     └──► Hybrid  → "What work was done on truck 62?" → SQL + docs → answer
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| PDF Extraction | `pdfplumber` |
| Entity Extraction | Rule-based regex (no API calls, no rate limits) |
| Structured Storage | DuckDB (local) / Delta Lake (Databricks) |
| Vector Store | ChromaDB + `sentence-transformers` (all-MiniLM-L6-v2) |
| LLM (Q&A only) | NVIDIA NIM — `meta/llama-3.1-70b-instruct` |
| Dashboard | Streamlit |
| Production | Databricks notebooks |
| Parallelism | ThreadPoolExecutor (12 workers for extraction) |

---

## Document Types Handled

| Type | Count | Key Fields Extracted |
|------|-------|----------------------|
| Maintenance Invoices | 77 | truck_unit, vendor, category, amount, technician, VIN |
| Vehicle Titles | 23 | VIN, make, model, year, odometer, title_no |
| CDL Licenses | 20 | driver_name, license_no, issued, **expiry_date** |
| IRS Form 2290 | 17 | VIN, tax_amount, period |
| Insurance Cards | 16 | truck_unit, policy_no, coverage, **expiry_date** |
| IRP Cards | 16 | plate_no, VIN, registration year |
| IFTA Fuel Tax Returns | 3 | account_no, total_tax, quarter |
| Equipment Leases | 1 | lease_no, truck_unit, amount |

---

## Key Metrics (Live from 197 documents)

- **$79,256** total fleet maintenance spend
- **Truck #19** is the highest cost unit — $36,150 across 7 service visits
- **4 CDL renewals** due within 90 days (Omar Haddad's expires **June 30**)
- **Top spend categories:** Engine ($20,700) · Tires ($17,492) · Brakes ($5,963)

---

## Project Structure

```
problem_statement_7/
├── config.py                  # Central config (paths, API keys via .env)
├── run_pipeline.py            # Two-stage ingestion pipeline (main entry point)
│
├── ingest/
│   ├── pdf_extractor.py       # pdfplumber parallel PDF text extraction
│   └── entity_extractor.py   # Rule-based entity extraction (9 doc types)
│
├── db/
│   ├── schema.py              # DuckDB schema + Gold views
│   └── loader.py             # Bronze/Silver upsert logic
│
├── vectors/
│   └── store.py              # ChromaDB add/search wrapper
│
├── query/
│   ├── router.py             # LLM-based question classifier (sql/rag/hybrid)
│   ├── sql_agent.py          # Text-to-SQL + execution
│   ├── rag_agent.py          # Semantic document retrieval
│   └── answer_engine.py      # Orchestrates routing → retrieval → synthesis
│
├── dashboard/
│   └── app.py                # Streamlit 4-page dashboard
│
├── databricks/
│   ├── 01_Bronze_Ingest.py   # PDF extraction → Delta table
│   ├── 02_Silver_Transform.py # Entity extraction → Delta table
│   ├── 03_Gold_Aggregate.py  # Spark SQL aggregations → Gold Delta tables
│   └── 04_Query_Engine.py    # Hybrid SQL + RAG query engine
│
└── pdf_datasets/             # 197 source PDFs
```

---

## Running Locally

### 1. Install dependencies

```bash
pip install pdfplumber duckdb chromadb sentence-transformers openai python-dotenv streamlit plotly pandas rich tqdm
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your NVIDIA NIM API key
```

### 3. Run the ingestion pipeline

```bash
python run_pipeline.py
```

Output:
```
[DB] Schema initialized
Found 197 documents
Stage 1: Parallel entity extraction (12 workers)...
Stage 2: Loading into DuckDB + ChromaDB...
✓ Done: 197/197 loaded successfully
```

### 4. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Open http://localhost:8501

---

## Dashboard Pages

| Page | What it shows |
|------|--------------|
| **Fleet Overview** | KPIs, top 10 trucks by cost, spend by category, monthly trend |
| **Ask Anything** | Natural language Q&A with source citations |
| **Documents** | Filterable document table + raw text viewer |
| **Alerts** | Expiring CDLs and insurance sorted by urgency |

---

## Running on Databricks

Upload the 4 notebooks from `databricks/` to your Databricks workspace and run them in order:

```
01_Bronze_Ingest.py      →  Reads PDFs from DBFS, writes Delta bronze table
02_Silver_Transform.py   →  Entity extraction, writes Delta silver table
03_Gold_Aggregate.py     →  Spark SQL aggregations, writes Gold Delta tables
04_Query_Engine.py       →  Interactive Q&A against Gold tables
```

**Required Databricks secrets:**
```
databricks secrets put --scope fleetoS --key NVIDIA_API_KEY --string-value <your-key>
```

---

## What Makes This Different

1. **No hallucinations** — SQL answers are grounded in the actual database; RAG answers cite specific document chunks. The LLM synthesizes, it doesn't invent.

2. **Zero rate-limit risk** — Entity extraction uses pure regex, not LLM calls. NVIDIA NIM is only hit once per user question.

3. **Automatic document type detection** — The classifier handles 9 document types without any training data, using domain-specific keyword rules.

4. **Two-stage parallel pipeline** — Extraction runs in parallel (12 workers), writes happen serially. Eliminates DuckDB write-write conflicts while keeping ingestion fast.

5. **Complete medallion architecture** — Bronze preserves raw text forever; Silver has structured entities; Gold has business-ready aggregations.

---

## Team

**Lone Rangers** — Hackathon 2026 · Data Pipeline Track · Databricks
