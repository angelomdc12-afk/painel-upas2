
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Painel Executivo UPAs", page_icon="🏥", layout="wide")

DATA_FILE = Path(__file__).parent / "dados_upas.xlsx"

MESES_COLS = list(range(2, 14))

def to_numeric(v):
    if pd.isna(v):
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    s = str(v).strip().replace("%", "")
    if not s:
        return np.nan
    try:
        return float(s)
    except:
        return np.nan

def to_minutes(v):
    if pd.isna(v):
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v) * 24 * 60
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return np.nan
    try:
        td = pd.to_timedelta(s)
        return td.total_seconds() / 60.0
    except:
        return np.nan

def fmt_int(v):
    if pd.isna(v):
        return "-"
    return f"{int(round(v)):,}".replace(",", ".")

def fmt_pct(v):
    if pd.isna(v):
        return "-"
    return f"{v:.1f}%".replace(".", ",")

def fmt_minutes(v):
    if pd.isna(v):
        return "-"
    total = int(round(v))
    d, rem = divmod(total, 1440)
    h, m = divmod(rem, 60)
    if d > 0:
        return f"{d}d {h:02d}:{m:02d}"
    return f"{h:02d}:{m:02d}"

@st.cache_data
def load_raw():
    return pd.read_excel(DATA_FILE, sheet_name=0, header=None)

def parse_block(df, unit_name, header_row):
    months = [str(df.iloc[header_row + 1, c]).strip() for c in MESES_COLS]
    recs = []

    def add_simple(metric, row, category="TOTAL", kind="value"):
        for i, c in enumerate(MESES_COLS):
            val = df.iloc[row, c]
            recs.append({
                "Unidade": unit_name, "Periodo": months[i], "Indicador": metric,
                "Categoria": category, "Valor": val, "Tipo": kind
            })

    def add_multi(metric, start_row, categories, kind="value"):
        for offs, cat in enumerate(categories):
            row = start_row + offs
            for i, c in enumerate(MESES_COLS):
                val = df.iloc[row, c]
                recs.append({
                    "Unidade": unit_name, "Periodo": months[i], "Indicador": metric,
                    "Categoria": cat, "Valor": val, "Tipo": kind
                })

    # Simple rows
    add_simple("PACIENTES RECEPCIONADOS", header_row + 2)
    add_simple("MÉDIA DIÁRIA", header_row + 3)
    add_simple("ATENDIMENTOS MÉDICOS", header_row + 4)
    add_simple("META ATENDIMENTOS MÉDICOS", header_row + 5)

    # Risk sections
    risk_cats = [
        "NÃO URGENTE (AZUL)",
        "POUCO URGENTE (VERDE)",
        "URGENTE (AMARELO)",
        "MUITO URGENTE (LARANJA)",
        "EMERGÊNCIA (VERMELHO)",
        "NÃO INFORMADO",
    ]
    add_multi("ATENDIMENTOS POR CLASSIFICAÇÃO DE RISCO", header_row + 6, risk_cats)
    add_simple("TOTAL ATENDIMENTOS POR CLASSIFICAÇÃO DE RISCO", header_row + 12)
    add_multi("PERCENTUAL POR CLASSIFICAÇÃO DE RISCO", header_row + 13, risk_cats, kind="percent")

    # Times
    add_simple("TEMPO DE ESPERA PARA CLASSIFICAÇÃO DE RISCO", header_row + 19, "MÉDIA GERAL", kind="time")
    add_simple("META TEMPO CLASSIFICAÇÃO", header_row + 20, "META", kind="time")
    add_simple("TEMPO MÉDIO DE ESPERA DE ATENDIMENTO MÉDICO", header_row + 21, "MÉDIA GERAL", kind="time")
    add_simple("TEMPO DE PERMANÊNCIA DE PACIENTES INTERNADOS", header_row + 22, "TEMPO MÉDIO DE PERMANÊNCIA GERAL", kind="time")
    add_simple("TEMPO DE PERMANÊNCIA DE PACIENTES SEM INTERNAÇÃO", header_row + 23, "TEMPO MÉDIO DE PERMANÊNCIA ATENDIMENTOS DE PORTA", kind="time")

    # Remoções
    add_simple("PERCENTUAL DE REMOÇÕES REALIZADAS POR USA", header_row + 24, "TOTAL", kind="value")

    # Exams
    exam_cats = ["RAIO-X", "PATOLOGIA CLÍNICA", "ELETROCARDIOGRAMA"]
    add_multi("EXAMES REALIZADOS", header_row + 25, exam_cats)
    add_simple("EXAMES REALIZADOS - TOTAL", header_row + 28)

    # Age
    age_cats = ["< 1 ANO", "1 - 4 ANOS", "5 - 9 ANOS", "10 - 14 ANOS", "15 - 19 ANOS", "20 - 39 ANOS", "40 - 49 ANOS", "50 - 59 ANOS", "60 OU MAIS"]
    add_multi("ATENDIMENTOS POR FAIXA ETÁRIA", header_row + 29, age_cats)
    add_simple("ATENDIMENTOS POR FAIXA ETÁRIA - TOTAL", header_row + 38)

    # City
    city_cats = ["DA CIDADE", "DE OUTRAS CIDADES"]
    add_multi("ATENDIMENTOS POR CIDADE", header_row + 39, city_cats)
    add_simple("ATENDIMENTOS POR CIDADE - TOTAL", header_row + 41)

    # Deaths
    add_simple("ÓBITOS", header_row + 42)

    out = pd.DataFrame(recs)
    out["ValorNum"] = np.where(out["Tipo"]=="time", out["Valor"].map(to_minutes), out["Valor"].map(to_numeric))
    out = out[~out["Periodo"].str.contains("nan", case=False, na=False)].copy()
    return out

@st.cache_data
def load_data():
    raw = load_raw()
    frames = [
        parse_block(raw, "UPA DE LUZIÂNIA - UPA II", 1),
        parse_block(raw, "UPA JARDIM INGÁ - UPA I", 46),
    ]
    df = pd.concat(frames, ignore_index=True)
    period_order = [p for p in df["Periodo"].dropna().unique().tolist()]
    df["Periodo"] = pd.Categorical(df["Periodo"], categories=period_order, ordered=True)
    return df, period_order

df, period_order = load_data()

# ---------- Sidebar ----------
st.sidebar.title("Filtros")
unit = st.sidebar.selectbox("Unidade", sorted(df["Unidade"].unique()))
start_period, end_period = st.sidebar.select_slider(
    "Período",
    options=period_order,
    value=(period_order[0], period_order[min(2, len(period_order)-1)])
)

selected_periods = period_order[period_order.index(start_period):period_order.index(end_period)+1]

base = df[(df["Unidade"] == unit) & (df["Periodo"].isin(selected_periods))].copy()

st.title("🏥 Painel Executivo de Monitoramento das UPAs")
st.caption("Visual executivo com foco em uma UPA por vez. Baseado na planilha operacional enviada.")

# ---------- KPI Cards ----------
def kpi_sum(indicador):
    d = base[(base["Indicador"] == indicador)]
    return d["ValorNum"].sum(min_count=1)

def kpi_mean(indicador):
    d = base[(base["Indicador"] == indicador)]
    return d["ValorNum"].mean()

k1 = kpi_sum("PACIENTES RECEPCIONADOS")
k2 = kpi_sum("ATENDIMENTOS MÉDICOS")
k3 = kpi_mean("TEMPO MÉDIO DE ESPERA DE ATENDIMENTO MÉDICO")
k4 = kpi_mean("TEMPO DE ESPERA PARA CLASSIFICAÇÃO DE RISCO")
k5 = kpi_sum("ÓBITOS")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Pacientes Recepcionados", fmt_int(k1))
c2.metric("Atendimentos Médicos", fmt_int(k2))
c3.metric("Tempo Médio Espera Médico", fmt_minutes(k3))
c4.metric("Tempo Espera Classificação", fmt_minutes(k4))
c5.metric("Óbitos", fmt_int(k5))

st.markdown("---")

# colors
risk_order = ["NÃO URGENTE (AZUL)", "POUCO URGENTE (VERDE)", "URGENTE (AMARELO)", "MUITO URGENTE (LARANJA)", "EMERGÊNCIA (VERMELHO)", "NÃO INFORMADO"]
exam_order = ["RAIO-X", "PATOLOGIA CLÍNICA", "ELETROCARDIOGRAMA"]
age_order = ["< 1 ANO", "1 - 4 ANOS", "5 - 9 ANOS", "10 - 14 ANOS", "15 - 19 ANOS", "20 - 39 ANOS", "40 - 49 ANOS", "50 - 59 ANOS", "60 OU MAIS"]
city_order = ["DA CIDADE", "DE OUTRAS CIDADES"]

# ---------- Helpers ----------
def line_chart(indicadores, title, is_time=False, show_legend=False):
    d = base[base["Indicador"].isin(indicadores)].copy()
    if d.empty:
        st.info(f"Sem dados para {title.lower()}.")
        return
    d = d.groupby(["Periodo", "Indicador"], as_index=False)["ValorNum"].sum()
    fig = px.line(d, x="Periodo", y="ValorNum", color="Indicador", markers=True, title=title)
    fig.update_layout(height=340, legend_title=None, showlegend=show_legend, margin=dict(l=10,r=10,t=50,b=10))
    if is_time:
        fig.update_yaxes(tickformat=",")
    st.plotly_chart(fig, use_container_width=True)

def bar_by_category(indicador, title, category_order=None, percent=False):
    d = base[base["Indicador"] == indicador].copy()
    if d.empty:
        st.info(f"Sem dados para {title.lower()}.")
        return
    d = d.groupby("Categoria", as_index=False)["ValorNum"].sum()
    if category_order:
        d["Categoria"] = pd.Categorical(d["Categoria"], categories=category_order, ordered=True)
        d = d.sort_values("Categoria")
    if percent:
        d["ValorNum"] = d["ValorNum"] * 100
    fig = px.bar(d, x="Categoria", y="ValorNum", title=title, text_auto=".1f" if percent else True)
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=50,b=10), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

def pie_by_category(indicador, title, category_order=None):
    d = base[base["Indicador"] == indicador].copy()
    if d.empty:
        st.info(f"Sem dados para {title.lower()}.")
        return
    d = d.groupby("Categoria", as_index=False)["ValorNum"].sum()
    if category_order:
        d["Categoria"] = pd.Categorical(d["Categoria"], categories=category_order, ordered=True)
        d = d.sort_values("Categoria")
    fig = px.pie(d, names="Categoria", values="ValorNum", title=title, hole=.45)
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Sections ----------
tab1, tab2, tab3 = st.tabs(["Visão Executiva", "Tempos Operacionais", "Perfil da Demanda"])

with tab1:
    a, b = st.columns(2)
    with a:
        line_chart(["PACIENTES RECEPCIONADOS"], "Pacientes Recepcionados por Período")
    with b:
        line_chart(["ATENDIMENTOS MÉDICOS", "META ATENDIMENTOS MÉDICOS"], "Atendimentos Médicos x Meta", show_legend=True)

    a, b = st.columns(2)
    with a:
        bar_by_category("ATENDIMENTOS POR CLASSIFICAÇÃO DE RISCO", "Atendimentos por Classificação de Risco", risk_order)
    with b:
        pie_by_category("ATENDIMENTOS POR CLASSIFICAÇÃO DE RISCO", "Percentual por Classificação de Risco", risk_order)

    a, b = st.columns(2)
    with a:
        bar_by_category("EXAMES REALIZADOS", "Exames Realizados", exam_order)
    with b:
        line_chart(["ÓBITOS"], "Óbitos por Período")

with tab2:
    a, b = st.columns(2)
    with a:
        line_chart(["TEMPO DE ESPERA PARA CLASSIFICAÇÃO DE RISCO", "META TEMPO CLASSIFICAÇÃO"], "Tempo de Espera para Classificação x Meta", is_time=True, show_legend=True)
    with b:
        line_chart(["TEMPO MÉDIO DE ESPERA DE ATENDIMENTO MÉDICO"], "Tempo Médio de Espera de Atendimento Médico", is_time=True)

    a, b = st.columns(2)
    with a:
        line_chart(["TEMPO DE PERMANÊNCIA DE PACIENTES INTERNADOS"], "Tempo de Permanência de Pacientes Internados", is_time=True)
    with b:
        line_chart(["TEMPO DE PERMANÊNCIA DE PACIENTES SEM INTERNAÇÃO"], "Tempo de Permanência de Pacientes sem Internação", is_time=True)

    st.plotly_chart(
        px.bar(
            base[base["Indicador"] == "PERCENTUAL DE REMOÇÕES REALIZADAS POR USA"].groupby("Periodo", as_index=False)["ValorNum"].sum(),
            x="Periodo", y="ValorNum", text_auto=True,
            title="Percentual de Remoções Realizadas por USA"
        ).update_layout(height=360, margin=dict(l=10,r=10,t=50,b=10)),
        use_container_width=True
    )

with tab3:
    a, b = st.columns(2)
    with a:
        bar_by_category("ATENDIMENTOS POR FAIXA ETÁRIA", "Atendimentos por Faixa Etária", age_order)
    with b:
        pie_by_category("ATENDIMENTOS POR CIDADE", "Atendimentos por Cidade", city_order)

    detail = base[base["Indicador"].isin([
        "PACIENTES RECEPCIONADOS", "ATENDIMENTOS MÉDICOS", "ÓBITOS",
        "TEMPO DE ESPERA PARA CLASSIFICAÇÃO DE RISCO", "TEMPO MÉDIO DE ESPERA DE ATENDIMENTO MÉDICO"
    ])].copy()
    detail["Valor Exibido"] = np.where(
        detail["Tipo"] == "time",
        detail["ValorNum"].map(fmt_minutes),
        detail["ValorNum"].map(lambda x: fmt_int(x) if pd.notna(x) else "-")
    )
    tabela = detail.pivot_table(index="Periodo", columns="Indicador", values="Valor Exibido", aggfunc="first")
    st.subheader("Resumo por período")
    st.dataframe(tabela, use_container_width=True)

st.markdown("---")
st.caption("Dica: para alimentar semanalmente ou diariamente no futuro, mantenha a estrutura por período na planilha e atualize o arquivo dados_upas.xlsx no repositório/app.")
