"""FleetOS Dashboard — Streamlit UI."""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.dirname(_here))

import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from config import DB_PATH
from query.answer_engine import answer

st.set_page_config(
    page_title="FleetOS — Sunflower Freight Lines",
    page_icon="🚛",
    layout="wide",
)

# ── helpers ────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return duckdb.connect(DB_PATH, read_only=True)

def q(sql, params=None):
    try:
        return get_conn().execute(sql, params or []).df()
    except Exception as e:
        return pd.DataFrame()

# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/semi-truck.png", width=64)
    st.title("FleetOS")
    st.caption("Sunflower Freight Lines LLC")
    st.divider()
    page = st.radio("Navigate", ["🏠 Fleet Overview", "💬 Ask Anything", "📄 Documents", "⚠️ Alerts"])

# ── Fleet Overview ─────────────────────────────────────────────────────────────
if page == "🏠 Fleet Overview":
    st.title("🚛 Fleet Overview")

    # KPI row
    total_trucks = q("SELECT COUNT(DISTINCT truck_unit) as n FROM silver_documents WHERE truck_unit IS NOT NULL AND truck_unit != ''")
    total_spend  = q("SELECT COALESCE(SUM(amount_total),0) as n FROM silver_documents WHERE doc_type='maintenance_invoice'")
    expiring_soon= q("SELECT COUNT(*) as n FROM gold_expiring_documents WHERE days_until_expiry <= 30")
    invoices     = q("SELECT COUNT(*) as n FROM silver_documents WHERE doc_type='maintenance_invoice'")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Trucks", int(total_trucks["n"].iloc[0]) if not total_trucks.empty else 0)
    c2.metric("Total Maintenance Spend", f"${float(total_spend['n'].iloc[0]):,.0f}" if not total_spend.empty else "$0")
    c3.metric("Docs Expiring < 30 Days", int(expiring_soon["n"].iloc[0]) if not expiring_soon.empty else 0)
    c4.metric("Maintenance Invoices", int(invoices["n"].iloc[0]) if not invoices.empty else 0)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 10 Trucks by Maintenance Cost")
        df = q("""
            SELECT truck_unit, COALESCE(total_maintenance_cost,0) AS total_cost, maintenance_count
            FROM gold_truck_summary
            ORDER BY total_cost DESC LIMIT 10
        """)
        if not df.empty:
            fig = px.bar(df, x="truck_unit", y="total_cost",
                         color="total_cost", color_continuous_scale="Reds",
                         labels={"truck_unit": "Truck", "total_cost": "Total Spend ($)"},
                         text_auto=".2s")
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Run the ingestion pipeline first.")

    with col2:
        st.subheader("Spend by Category")
        df = q("""
            SELECT category, SUM(amount_total) AS total
            FROM silver_documents
            WHERE doc_type='maintenance_invoice' AND category IS NOT NULL
            GROUP BY category ORDER BY total DESC
        """)
        if not df.empty:
            fig = px.pie(df, values="total", names="category", hole=0.4)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No invoice data yet.")

    st.subheader("Monthly Maintenance Spend")
    df = q("""
        SELECT strftime(month, '%Y-%m') AS month, SUM(total_spend) AS spend
        FROM gold_monthly_spend
        GROUP BY month ORDER BY month
    """)
    if not df.empty:
        fig = px.line(df, x="month", y="spend", markers=True,
                      labels={"month": "Month", "spend": "Spend ($)"})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Truck Summary Table")
    df = q("SELECT * FROM gold_truck_summary")
    if not df.empty:
        st.dataframe(df, use_container_width=True)

# ── Ask Anything ──────────────────────────────────────────────────────────────
elif page == "💬 Ask Anything":
    st.title("💬 Ask Anything")
    st.caption("Ask in plain English. FleetOS searches structured data and documents together.")

    examples = [
        "Which trucks are most expensive to maintain?",
        "How much did I spend on parts last month?",
        "When does truck 84's insurance expire?",
        "Where is the bill of sale for truck 21?",
        "What documents do I need to renew the plates for truck 37?",
        "Which driver's CDL expires soonest?",
        "Show me all maintenance done on truck 62",
    ]

    with st.expander("Example questions"):
        for ex in examples:
            if st.button(ex, key=ex):
                st.session_state["user_q"] = ex

    question = st.text_input(
        "Your question:",
        value=st.session_state.get("user_q", ""),
        placeholder="e.g. How much did I spend on truck 62 last month?",
    )

    if st.button("Ask", type="primary") and question:
        with st.spinner("Thinking..."):
            result = answer(question)

        st.markdown("### Answer")
        st.success(result["answer"])

        with st.expander(f"Strategy: {result['strategy'].upper()} | Sources: {len(result['sources'])}"):
            if result.get("sql"):
                st.code(result["sql"]["sql"], language="sql")
                if result["sql"]["rows"]:
                    st.dataframe(pd.DataFrame(result["sql"]["rows"]))
                if result["sql"]["error"]:
                    st.error(result["sql"]["error"])
            if result["sources"]:
                st.write("**Documents referenced:**")
                for s in result["sources"]:
                    st.write(f"  • {s}")

# ── Documents ──────────────────────────────────────────────────────────────────
elif page == "📄 Documents":
    st.title("📄 Document Registry")

    doc_types = q("SELECT DISTINCT doc_type FROM silver_documents WHERE doc_type IS NOT NULL ORDER BY doc_type")
    trucks     = q("SELECT DISTINCT truck_unit FROM silver_documents WHERE truck_unit IS NOT NULL AND truck_unit != '' ORDER BY CAST(truck_unit AS INTEGER)")

    c1, c2, c3 = st.columns(3)
    with c1:
        type_filter = st.selectbox("Document Type", ["All"] + list(doc_types["doc_type"]))
    with c2:
        truck_filter = st.selectbox("Truck Unit", ["All"] + list(trucks["truck_unit"]))
    with c3:
        search_text = st.text_input("Search", "")

    # All columns — shown selectively based on which are non-null for the result
    ALL_COLS = "filename, doc_type, truck_unit, vin, date, expiry_date, amount_total, vendor, driver_name, policy_no, make, model, year, plate_no, category, technician, buyer_name, seller_name, odometer"
    sql = f"SELECT {ALL_COLS} FROM silver_documents WHERE 1=1"
    params = []
    if type_filter != "All":
        sql += " AND doc_type = ?"
        params.append(type_filter)
    if truck_filter != "All":
        sql += " AND truck_unit = ?"
        params.append(truck_filter)
    if search_text:
        sql += " AND (filename ILIKE ? OR vendor ILIKE ? OR driver_name ILIKE ?)"
        like = f"%{search_text}%"
        params.extend([like, like, like])
    sql += " ORDER BY date DESC NULLS LAST LIMIT 200"

    df = q(sql, params)
    st.write(f"**{len(df)} documents**")
    if not df.empty:
        # Drop columns that are entirely null for the current filter — keeps table clean
        df_display = df.dropna(axis=1, how="all")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        selected = st.selectbox("View document text:", ["—"] + list(df["filename"]))
        if selected != "—":
            raw = q("SELECT raw_text FROM bronze_documents WHERE filename = ?", [selected])
            if not raw.empty:
                st.text_area("Raw Document Text", raw["raw_text"].iloc[0], height=400)

# ── Alerts ─────────────────────────────────────────────────────────────────────
elif page == "⚠️ Alerts":
    st.title("⚠️ Expiring Documents & Alerts")

    df = q("SELECT * FROM gold_expiring_documents ORDER BY days_until_expiry")
    if not df.empty:
        critical = df[df["days_until_expiry"] <= 30]
        warning  = df[(df["days_until_expiry"] > 30) & (df["days_until_expiry"] <= 60)]
        ok       = df[df["days_until_expiry"] > 60]

        if not critical.empty:
            st.error(f"🔴 {len(critical)} documents expiring within 30 days")
            st.dataframe(critical, use_container_width=True, hide_index=True)

        if not warning.empty:
            st.warning(f"🟡 {len(warning)} documents expiring in 31–60 days")
            st.dataframe(warning, use_container_width=True, hide_index=True)

        if not ok.empty:
            st.success(f"🟢 {len(ok)} documents expiring in 61–90 days")
            st.dataframe(ok, use_container_width=True, hide_index=True)
    else:
        st.info("No expiring documents found — or run the ingestion pipeline first.")
