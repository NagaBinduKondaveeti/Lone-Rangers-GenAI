"""FleetOS Dashboard — Instrument-cluster HUD design."""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.dirname(_here))

import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import date

from query.answer_engine import answer

# Compute DB_PATH from this file's location — avoids CWD-relative import issues
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_project_root, "data", "fleet.db")

st.set_page_config(
    page_title="FleetOS — Sunflower Freight Lines",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global theme ────────────────────────────────────────────────────────────────
# st.html() avoids the Streamlit 1.3x+ bug where <style> inside st.markdown()
# also renders as visible text content alongside the injected styles.
st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#060B18;--mid:#0D1B35;--card:rgba(14,26,52,0.65);
  --amber:#FF6B2B;--amber-glow:rgba(255,107,43,0.35);--amber-dim:rgba(255,107,43,0.12);
  --cyan:#00C2FF;--cyan-glow:rgba(0,194,255,0.35);--cyan-dim:rgba(0,194,255,0.1);
  --green:#00FF88;--red:#FF3B5C;
  --text:#E8EEFF;--muted:#4A6080;--border:rgba(255,107,43,0.18);
}

/* ── Shell ── */
.stApp{
  background:radial-gradient(ellipse 120% 80% at 10% 10%,#0D1B35 0%,#060B18 55%),
             radial-gradient(ellipse 60% 60% at 90% 80%,#0A1A30 0%,#060B18 60%);
  background-attachment:fixed;
  font-family:'Inter',sans-serif;
  color:var(--text);
}
/* Scanline — the signature texture */
.stApp::after{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:9998;
  background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.018) 3px,rgba(0,0,0,0.018) 4px);
}

/* ── Sidebar ── */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#091220 0%,#060B18 100%) !important;
  border-right:1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child{padding-top:0 !important;}

/* ── Radio ── */
[data-testid="stRadio"] > label{display:none;}
[data-testid="stRadio"] label{
  color:var(--muted) !important;font-family:'Inter',sans-serif !important;
  font-size:12px !important;font-weight:600 !important;
  letter-spacing:0.12em !important;text-transform:uppercase !important;
  transition:color .15s !important;padding:10px 0 !important;
}
[data-testid="stRadio"] label:hover{color:var(--text) !important;}
[data-testid="stRadio"] [aria-checked="true"] ~ div label{color:var(--amber) !important;}

/* ── Typography ── */
h1,h2,h3{font-family:'Bebas Neue',sans-serif !important;letter-spacing:.06em !important;color:var(--text) !important;}

/* ── Dataframe ── */
[data-testid="stDataFrame"]{border:1px solid var(--border) !important;border-radius:10px !important;background:var(--card) !important;backdrop-filter:blur(12px);}
thead th{background:rgba(255,107,43,0.08) !important;color:var(--amber) !important;font-family:'JetBrains Mono',monospace !important;font-size:10px !important;letter-spacing:.12em !important;text-transform:uppercase !important;border-bottom:1px solid var(--border) !important;}
tbody td{color:var(--text) !important;font-family:'JetBrains Mono',monospace !important;font-size:11px !important;border-color:rgba(255,255,255,0.03) !important;}
tbody tr:hover td{background:rgba(255,107,43,0.04) !important;}

/* ── Inputs ── */
.stTextInput input,.stTextArea textarea{
  background:var(--card) !important;border:1px solid var(--border) !important;
  color:var(--text) !important;border-radius:8px !important;
  font-family:'Inter',sans-serif !important;backdrop-filter:blur(8px);
}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:var(--amber) !important;
  box-shadow:0 0 0 2px var(--amber-dim),0 0 12px var(--amber-dim) !important;
  outline:none !important;
}

/* ── Buttons ── */
.stButton>button{
  background:linear-gradient(135deg,#FF6B2B 0%,#FF8844 100%) !important;
  color:#060B18 !important;border:none !important;border-radius:8px !important;
  font-family:'Bebas Neue',sans-serif !important;font-size:18px !important;
  letter-spacing:.12em !important;padding:10px 32px !important;
  transition:all .2s !important;
  box-shadow:0 4px 20px rgba(255,107,43,0.4) !important;
}
.stButton>button:hover{transform:translateY(-2px) !important;box-shadow:0 8px 30px rgba(255,107,43,0.6) !important;}

/* ── Selectbox ── */
[data-baseweb="select"]>div{
  background:var(--card) !important;border:1px solid var(--border) !important;
  color:var(--text) !important;border-radius:8px !important;
  font-family:'Inter',sans-serif !important;
}

/* ── Alert boxes ── */
[data-testid="stAlert"]{background:var(--card) !important;border-radius:10px !important;backdrop-filter:blur(12px);border-left-width:3px !important;}

/* ── Expander ── */
[data-testid="stExpander"]{background:var(--card) !important;border:1px solid var(--border) !important;border-radius:10px !important;backdrop-filter:blur(12px);}
[data-testid="stExpander"] summary{color:var(--muted) !important;font-size:12px !important;font-weight:600 !important;letter-spacing:.08em !important;}

/* ── Spinner ── */
[data-testid="stSpinner"]>div{border-top-color:var(--amber) !important;}

/* ── Divider ── */
hr{border-color:var(--border) !important;margin:24px 0 !important;}

/* ── Code ── */
.stCode code{background:#091220 !important;color:#00FF88 !important;font-family:'JetBrains Mono',monospace !important;font-size:12px !important;}

/* ── Success/warning/error ── */
[data-testid="stSuccess"]{border-left-color:var(--green) !important;background:rgba(0,255,136,0.06) !important;}
[data-testid="stWarning"]{border-left-color:#FFB347 !important;background:rgba(255,179,71,0.06) !important;}
[data-testid="stError"]{border-left-color:var(--red) !important;background:rgba(255,59,92,0.06) !important;}

/* ── Caption ── */
.stCaption{color:var(--muted) !important;font-size:11px !important;letter-spacing:.06em !important;}

/* ── KPI card hover ── */
.kpi-wrap:hover .kpi-card{transform:translateY(-4px);border-color:rgba(255,107,43,.45);}
.kpi-card{transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease;}
</style>
""")

# ── DB helper ───────────────────────────────────────────────────────────────────
def q(sql, params=None):
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        df = con.execute(sql, params or []).df()
        con.close()
        return df
    except Exception as e:
        import traceback; traceback.print_exc()
        return pd.DataFrame()

# ── Plotly dark theme ───────────────────────────────────────────────────────────
def dark_layout(fig, height=320):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(8,18,36,0.5)',
        font=dict(family='Inter', color='#8899BB', size=11),
        height=height, margin=dict(l=12, r=12, t=36, b=12),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#8899BB', size=10)),
    )
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.03)', linecolor='rgba(255,107,43,0.15)',
                     tickfont=dict(family='JetBrains Mono', color='#4A6080', size=10),
                     title_font=dict(color='#4A6080'))
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.03)', linecolor='rgba(255,107,43,0.15)',
                     tickfont=dict(family='JetBrains Mono', color='#4A6080', size=10),
                     title_font=dict(color='#4A6080'))
    return fig

# ── KPI card component ──────────────────────────────────────────────────────────
def kpi_cards(cards):
    """cards = list of (label, value_str, icon, color_key)"""
    palette = {
        'amber': ('var(--amber)', 'rgba(255,107,43,0.13)', '0 0 28px rgba(255,107,43,0.3)'),
        'cyan':  ('var(--cyan)',  'rgba(0,194,255,0.10)',  '0 0 28px rgba(0,194,255,0.25)'),
        'green': ('var(--green)', 'rgba(0,255,136,0.10)',  '0 0 28px rgba(0,255,136,0.2)'),
        'red':   ('var(--red)',   'rgba(255,59,92,0.12)',  '0 0 28px rgba(255,59,92,0.25)'),
    }
    inner = ''
    for label, value_str, icon, color_key in cards:
        clr, bg, glow = palette.get(color_key, palette['amber'])
        inner += f"""
        <div class="kpi-wrap" style="flex:1;min-width:160px;">
          <div class="kpi-card" style="
            background:{bg};
            border:1px solid {clr}33;
            border-radius:14px;padding:22px 20px;
            position:relative;overflow:hidden;
            box-shadow:inset 0 1px 0 rgba(255,255,255,0.05);
          ">
            <div style="position:absolute;top:-18px;right:-18px;width:72px;height:72px;
                        border-radius:50%;background:radial-gradient(circle,{clr}22 0%,transparent 70%);"></div>
            <div style="font-size:24px;margin-bottom:10px;filter:drop-shadow(0 0 6px {clr});">{icon}</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:44px;line-height:1;
                        color:{clr};text-shadow:0 0 24px {clr}88;letter-spacing:.02em;">{value_str}</div>
            <div style="font-family:'Inter',sans-serif;font-size:10px;font-weight:700;
                        letter-spacing:.14em;text-transform:uppercase;color:#3A5070;margin-top:8px;">{label}</div>
          </div>
        </div>"""
    st.markdown(f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:28px;">{inner}</div>',
                unsafe_allow_html=True)

# ── Section header ──────────────────────────────────────────────────────────────
def section_header(title, accent='amber'):
    clr = 'var(--amber)' if accent == 'amber' else 'var(--cyan)'
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin:20px 0 10px;">
      <div style="width:3px;height:22px;background:{clr};border-radius:2px;
                  box-shadow:0 0 8px {clr};flex-shrink:0;"></div>
      <div style="font-family:'Bebas Neue',sans-serif;font-size:20px;
                  letter-spacing:.1em;color:#E8EEFF;">{title}</div>
    </div>""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:28px 16px 20px;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:36px;letter-spacing:.12em;
                  background:linear-gradient(90deg,#FF6B2B 0%,#FF9A5C 100%);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  background-clip:text;line-height:1;">FLEETOS</div>
      <div style="font-size:9px;color:#2A3F5F;letter-spacing:.22em;
                  text-transform:uppercase;margin-top:2px;padding-left:2px;">
        Sunflower Freight Lines
      </div>
      <div style="height:1px;background:linear-gradient(90deg,#FF6B2B55,transparent);margin-top:16px;"></div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("nav", [
        "🏠  Fleet Overview",
        "💬  Ask Anything",
        "📄  Documents",
        "⚠️  Alerts",
    ], label_visibility="collapsed")

    st.markdown("""
    <div style="position:absolute;bottom:20px;left:0;right:0;padding:0 16px;">
      <div style="height:1px;background:linear-gradient(90deg,transparent,#FF6B2B33,transparent);margin-bottom:12px;"></div>
      <div style="font-size:9px;color:#1E2E44;letter-spacing:.16em;text-transform:uppercase;text-align:center;">
        197 PDFs · 9 doc types · AI-powered
      </div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# FLEET OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠  Fleet Overview":
    st.markdown("""
    <div style="padding:4px 0 20px;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:56px;line-height:1;letter-spacing:.05em;">
        FLEET&nbsp;<span style="color:#FF6B2B;text-shadow:0 0 40px rgba(255,107,43,0.5);">COMMAND</span>
      </div>
      <div style="font-size:10px;color:#2A3F5F;letter-spacing:.2em;text-transform:uppercase;margin-top:4px;">
        Live operational intelligence · Wichita, KS
      </div>
    </div>
    """, unsafe_allow_html=True)

    total_trucks  = q("SELECT COUNT(DISTINCT truck_unit) as n FROM silver_documents WHERE truck_unit IS NOT NULL AND truck_unit != ''")
    total_spend   = q("SELECT COALESCE(SUM(amount_total),0) as n FROM silver_documents WHERE doc_type='maintenance_invoice'")
    expiring_soon = q("SELECT COUNT(*) as n FROM gold_expiring_documents WHERE days_until_expiry <= 30")
    invoices      = q("SELECT COUNT(*) as n FROM silver_documents WHERE doc_type='maintenance_invoice'")

    n_trucks = int(total_trucks["n"].iloc[0]) if not total_trucks.empty else 0
    n_spend  = float(total_spend["n"].iloc[0]) if not total_spend.empty else 0
    n_alerts = int(expiring_soon["n"].iloc[0]) if not expiring_soon.empty else 0
    n_inv    = int(invoices["n"].iloc[0]) if not invoices.empty else 0

    kpi_cards([
        ("Active Trucks",       str(n_trucks),              "🚛", "amber"),
        ("Maintenance Spend",   f"${n_spend/1000:.0f}K",    "💰", "cyan"),
        ("Expiring ≤ 30 Days",  str(n_alerts),              "⚠️", "red" if n_alerts else "green"),
        ("Invoices Ingested",   str(n_inv),                 "📋", "green"),
    ])

    # ── Charts ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns([3, 2])

    with col1:
        section_header("TOP TRUCKS BY MAINTENANCE COST")
        df = q("""SELECT truck_unit, COALESCE(total_maintenance_cost,0) AS cost, maintenance_count
                  FROM gold_truck_summary ORDER BY cost DESC LIMIT 10""")
        if not df.empty:
            REDS = ['#1A2E4A','#1E3558','#FF6B2B','#FF3B5C']
            norm = (df["cost"] - df["cost"].min()) / (df["cost"].max() - df["cost"].min() + 1)
            bar_colors = [f'rgba({int(255*n)},{int(107*(1-n)+43*n)},{int(43*(1-n)+20*n)},0.9)'
                          for n in norm]
            fig = go.Figure(go.Bar(
                x=df["truck_unit"], y=df["cost"],
                marker=dict(
                    color=df["cost"],
                    colorscale=[[0,'#162540'],[0.4,'#FF6B2B'],[1,'#FF3B5C']],
                    line=dict(color='rgba(255,107,43,0.25)', width=1),
                ),
                text=[f'${v:,.0f}' for v in df["cost"]],
                textposition='outside', textfont=dict(family='JetBrains Mono', size=9, color='#4A6080'),
                hovertemplate='<b>Truck %{x}</b><br><b>$%{y:,.0f}</b><extra></extra>',
            ))
            dark_layout(fig, 300)
            fig.update_layout(showlegend=False, title=dict(text=''))
            fig.update_xaxes(title_text='')
            fig.update_yaxes(tickprefix='$', tickformat=',.0f', title_text='')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col2:
        section_header("SPEND BY CATEGORY")
        df_cat = q("""SELECT category, SUM(amount_total) AS total FROM silver_documents
                      WHERE doc_type='maintenance_invoice' AND category IS NOT NULL
                      GROUP BY category ORDER BY total DESC""")
        if not df_cat.empty:
            PALETTE = ['#FF6B2B','#00C2FF','#00FF88','#FF3B5C','#FFB347',
                       '#7B61FF','#FF6BB5','#3BE8FF','#FFD700','#A8FF78','#FF8C42','#5CFFD6']
            fig2 = go.Figure(go.Pie(
                labels=df_cat["category"], values=df_cat["total"], hole=0.6,
                marker=dict(colors=PALETTE[:len(df_cat)],
                            line=dict(color='#060B18', width=2)),
                textfont=dict(family='JetBrains Mono', size=9, color='#E8EEFF'),
                hovertemplate='<b>%{label}</b><br>$%{value:,.0f} · %{percent}<extra></extra>',
                showlegend=True,
            ))
            top = df_cat.iloc[0]["category"] if not df_cat.empty else ''
            fig2.add_annotation(text=top.upper(), x=0.5, y=0.55, showarrow=False,
                                font=dict(family='Bebas Neue', size=14, color='#FF6B2B'))
            fig2.add_annotation(text='TOP', x=0.5, y=0.42, showarrow=False,
                                font=dict(family='Inter', size=9, color='#3A5070'))
            dark_layout(fig2, 300)
            fig2.update_layout(legend=dict(
                font=dict(family='JetBrains Mono', size=9, color='#4A6080'),
                bgcolor='rgba(0,0,0,0)', itemsizing='constant',
            ))
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    section_header("MONTHLY MAINTENANCE TREND", "cyan")
    df_m = q("SELECT strftime(month,'%Y-%m') AS month, SUM(total_spend) AS spend FROM gold_monthly_spend GROUP BY month ORDER BY month")
    if not df_m.empty:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df_m["month"], y=df_m["spend"],
            fill='tozeroy', fillcolor='rgba(0,194,255,0.06)',
            line=dict(color='#00C2FF', width=2.5, shape='spline', smoothing=1.2),
            marker=dict(color='#00C2FF', size=5, line=dict(color='#060B18', width=2)),
            hovertemplate='<b>%{x}</b><br>$%{y:,.0f}<extra></extra>',
        ))
        dark_layout(fig3, 220)
        fig3.update_yaxes(tickprefix='$', tickformat=',.0f')
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

    section_header("FLEET MASTER SUMMARY")
    df_fleet = q("SELECT * FROM gold_truck_summary")
    if not df_fleet.empty:
        st.dataframe(df_fleet, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# ASK ANYTHING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬  Ask Anything":
    st.markdown("""
    <div style="padding:4px 0 20px;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:56px;line-height:1;letter-spacing:.05em;">
        ASK&nbsp;<span style="color:#00C2FF;text-shadow:0 0 40px rgba(0,194,255,0.5);">ANYTHING</span>
      </div>
      <div style="font-size:10px;color:#2A3F5F;letter-spacing:.2em;text-transform:uppercase;margin-top:4px;">
        Hybrid RAG + SQL · LLaMA 3.1 70B via NVIDIA NIM
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Example chips
    examples = [
        "Which truck costs the most to maintain?",
        "When does truck 84's insurance expire?",
        "Which driver's CDL expires soonest?",
        "Show all maintenance on truck 62",
        "What's the total spend on tires?",
        "Where is the bill of sale for truck 21?",
        "How much did I spend on parts last month?",
    ]
    chips_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">'
    for ex in examples:
        chips_html += f"""
        <span onclick="(function(){{
          var inp=window.parent.document.querySelector('.stTextInput input');
          if(inp){{inp.value='{ex}';inp.dispatchEvent(new Event('input',{{bubbles:true}}));}}
        }})()" style="
          cursor:pointer;padding:6px 14px;border-radius:20px;
          border:1px solid rgba(0,194,255,0.25);
          background:rgba(0,194,255,0.06);
          font-size:11px;color:#5C8099;font-family:'Inter',sans-serif;
          transition:all .15s;white-space:nowrap;
        " onmouseenter="this.style.borderColor='rgba(0,194,255,0.6)';this.style.color='#00C2FF'"
           onmouseleave="this.style.borderColor='rgba(0,194,255,0.25)';this.style.color='#5C8099'">
          {ex}
        </span>"""
    chips_html += '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

    question = st.text_input("", value=st.session_state.get("user_q", ""),
                             placeholder="Ask about costs, compliance, documents, drivers…",
                             label_visibility="collapsed")

    if st.button("▶  QUERY FLEET INTELLIGENCE") and question:
        with st.spinner("Routing query…"):
            result = answer(question)

        st.markdown(f"""
        <div style="background:rgba(0,194,255,0.06);border:1px solid rgba(0,194,255,0.25);
                    border-radius:12px;padding:20px 24px;margin:16px 0;
                    border-left:3px solid #00C2FF;">
          <div style="font-size:10px;color:#2A4A60;letter-spacing:.14em;
                      text-transform:uppercase;margin-bottom:10px;font-weight:600;">Answer</div>
          <div style="font-family:'Inter',sans-serif;font-size:15px;color:#D0E8FF;
                      line-height:1.65;">{result["answer"]}</div>
        </div>
        """, unsafe_allow_html=True)

        strategy_color = {'sql': '#FF6B2B', 'rag': '#00C2FF', 'hybrid': '#00FF88'}.get(result['strategy'], '#FF6B2B')
        with st.expander(f"Strategy: {result['strategy'].upper()} · {len(result['sources'])} source(s)"):
            if result.get("sql") and result["sql"].get("sql"):
                st.code(result["sql"]["sql"], language="sql")
                if result["sql"]["rows"]:
                    st.dataframe(pd.DataFrame(result["sql"]["rows"]), hide_index=True)
                if result["sql"].get("error"):
                    st.error(result["sql"]["error"])
            if result["sources"]:
                st.markdown("**Documents referenced:**")
                for s in result["sources"]:
                    st.markdown(f"  `{s}`")

# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📄  Documents":
    st.markdown("""
    <div style="padding:4px 0 20px;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:56px;line-height:1;letter-spacing:.05em;">
        DOCUMENT&nbsp;<span style="color:#FF6B2B;text-shadow:0 0 40px rgba(255,107,43,0.5);">REGISTRY</span>
      </div>
      <div style="font-size:10px;color:#2A3F5F;letter-spacing:.2em;text-transform:uppercase;margin-top:4px;">
        197 PDFs · 9 document types · medallion architecture
      </div>
    </div>
    """, unsafe_allow_html=True)

    doc_types = q("SELECT DISTINCT doc_type FROM silver_documents WHERE doc_type IS NOT NULL ORDER BY doc_type")
    trucks    = q("SELECT DISTINCT truck_unit FROM silver_documents WHERE truck_unit IS NOT NULL AND truck_unit != '' ORDER BY CAST(truck_unit AS INTEGER)")

    c1, c2, c3 = st.columns(3)
    with c1:
        type_filter = st.selectbox("Document Type", ["All"] + list(doc_types["doc_type"]))
    with c2:
        truck_filter = st.selectbox("Truck Unit", ["All"] + list(trucks["truck_unit"]))
    with c3:
        search_text = st.text_input("Search", "", placeholder="filename / vendor / driver…")

    ALL_COLS = "filename, doc_type, truck_unit, vin, date, expiry_date, amount_total, vendor, driver_name, policy_no, make, model, year, plate_no, category, technician, buyer_name, seller_name, odometer"
    sql = f"SELECT {ALL_COLS} FROM silver_documents WHERE 1=1"
    params = []
    if type_filter != "All":
        sql += " AND doc_type = ?"; params.append(type_filter)
    if truck_filter != "All":
        sql += " AND truck_unit = ?"; params.append(truck_filter)
    if search_text:
        sql += " AND (filename ILIKE ? OR vendor ILIKE ? OR driver_name ILIKE ?)";
        like = f"%{search_text}%"; params.extend([like, like, like])
    sql += " ORDER BY date DESC NULLS LAST LIMIT 200"

    df = q(sql, params)
    st.markdown(f'<div style="font-size:11px;color:#3A5070;letter-spacing:.1em;margin-bottom:8px;">{len(df)} DOCUMENTS</div>', unsafe_allow_html=True)
    if not df.empty:
        df_display = df.dropna(axis=1, how='all')
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        selected = st.selectbox("Inspect document:", ["—"] + list(df["filename"]))
        if selected != "—":
            raw = q("SELECT raw_text FROM bronze_documents WHERE filename = ?", [selected])
            if not raw.empty:
                st.markdown(f'<div style="font-size:10px;color:#3A5070;letter-spacing:.1em;margin-bottom:6px;">RAW TEXT · {selected}</div>', unsafe_allow_html=True)
                st.text_area("", raw["raw_text"].iloc[0], height=380, label_visibility="collapsed")

# ══════════════════════════════════════════════════════════════════════════════
# ALERTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚠️  Alerts":
    st.markdown("""
    <div style="padding:4px 0 20px;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:56px;line-height:1;letter-spacing:.05em;">
        COMPLIANCE&nbsp;<span style="color:#FF3B5C;text-shadow:0 0 40px rgba(255,59,92,0.5);">ALERTS</span>
      </div>
      <div style="font-size:10px;color:#2A3F5F;letter-spacing:.2em;text-transform:uppercase;margin-top:4px;">
        Expiring CDLs · Insurance · Registrations · Next 90 days
      </div>
    </div>
    """, unsafe_allow_html=True)

    df = q("SELECT * FROM gold_expiring_documents ORDER BY days_until_expiry")

    if not df.empty:
        critical = df[df["days_until_expiry"] <= 30]
        warning  = df[(df["days_until_expiry"] > 30) & (df["days_until_expiry"] <= 60)]
        ok       = df[df["days_until_expiry"] > 60]

        # Inline alert cards
        for _, row in df.iterrows():
            days = int(row["days_until_expiry"])
            if days <= 30:
                clr, bg, label = '#FF3B5C', 'rgba(255,59,92,0.08)', 'CRITICAL'
            elif days <= 60:
                clr, bg, label = '#FFB347', 'rgba(255,179,71,0.08)', 'WARNING'
            else:
                clr, bg, label = '#00FF88', 'rgba(0,255,136,0.06)', 'OK'

            driver = row.get("driver_name") or "—"
            truck  = row.get("truck_unit") or "—"
            dtype  = str(row.get("doc_type") or "").replace("_", " ").upper()
            expiry = str(row.get("expiry_date") or "")[:10]

            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:16px;
                        background:{bg};border:1px solid {clr}33;
                        border-left:3px solid {clr};border-radius:10px;
                        padding:14px 20px;margin-bottom:8px;">
              <div style="font-family:'Bebas Neue',sans-serif;font-size:36px;
                          color:{clr};text-shadow:0 0 16px {clr}88;
                          line-height:1;min-width:52px;text-align:center;">{days}</div>
              <div style="font-size:9px;color:{clr}88;letter-spacing:.1em;
                          text-transform:uppercase;min-width:48px;text-align:center;">days</div>
              <div style="flex:1;">
                <div style="font-family:'Inter',sans-serif;font-size:13px;
                            font-weight:600;color:#D0D8F0;">{driver}</div>
                <div style="font-size:10px;color:#3A5070;margin-top:2px;
                            font-family:'JetBrains Mono',monospace;">
                  {dtype} · Truck {truck} · Exp {expiry}
                </div>
              </div>
              <div style="font-family:'Bebas Neue',sans-serif;font-size:13px;
                          letter-spacing:.14em;color:{clr};padding:4px 10px;
                          border:1px solid {clr}44;border-radius:4px;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        section_header(f"ALL {len(df)} EXPIRING DOCUMENTS")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div style="background:rgba(0,255,136,0.06);border:1px solid rgba(0,255,136,0.2);
                    border-radius:12px;padding:32px;text-align:center;">
          <div style="font-family:'Bebas Neue',sans-serif;font-size:32px;color:#00FF88;">ALL CLEAR</div>
          <div style="font-size:12px;color:#2A4A3A;margin-top:8px;">No documents expiring in the next 90 days</div>
        </div>
        """, unsafe_allow_html=True)
