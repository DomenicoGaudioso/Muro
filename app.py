# -*- coding: utf-8 -*-
import json

import streamlit as st

from src import (
    DEFAULT_STRAT,
    DatiMuro,
    analisi_stabilita_pendio,
    calcola_muro,
    export_json,
    figura_geometria,
    figura_output,
    figura_pendio,
    genera_note,
    genera_warning,
    tabella_sintesi,
    tabella_sollecitazioni,
    valida_dati,
)
from src_report import create_pdf_report, create_word_report

DEFAULTS = {
    "H": 5.0,
    "q": 10.0,
    "gamma_cls": 24.0,
    "B": 3.5,
    "B_punta": 1.0,
    "B_tallone": 2.5,
    "t_base": 0.5,
    "t_fusto_top": 0.30,
    "t_fusto_bot": 0.50,
    "mu_base": 0.55,
    "q_amm": 250.0,
    "h_fronte": 0.5,
    "falda_retro": 99.0,
    "falda_fronte": 99.0,
    "kh": 0.15,
    "kv": 0.05,
    "delta_muro": 20.0,
    "include_passivo": True,
    "stratigrafia_csv": DEFAULT_STRAT,
    "ha_tirante": False,
    "t_quota": 4.0,
    "t_inclinazione": 15.0,
    "t_tiro": 150.0,
    "analizza_pendio": True,
    "pendio_H": 5.0,
    "pendio_beta": 26.0,
    "pendio_berma": 6.0,
}

DESIGN_REFERENCES = [
    "NTC 2018, Capitolo 6.5 - opere di sostegno: azioni, drenaggio, riempimenti e verifiche del complesso opera-terreno.",
    "Circolare 21/01/2019 n. 7 C.S.LL.PP., C6.5.3.1.1: SLU GEO per ribaltamento, scorrimento, carico limite e stabilita globale.",
    "EN 1997-1, Sezione 9: stati limite delle strutture di sostegno, pressioni idrauliche, scorrimento, ribaltamento e portanza.",
]

PREMIUM_CSS = """
<style>
  :root {
    --ink: #13202b;
    --muted: #5b6774;
    --line: rgba(19, 32, 43, 0.12);
    --paper: #f6f7f8;
    --panel: #ffffff;
    --accent: #155e75;
    --ok: #166534;
    --warn: #a16207;
    --bad: #b91c1c;
  }
  .stApp {
    background: linear-gradient(180deg, #f7f8fa 0%, #eef2f5 100%);
  }
  .block-container {
    padding-top: 1.4rem;
    padding-bottom: 2rem;
  }
  .hero-shell {
    border: 1px solid rgba(255,255,255,.22);
    background: linear-gradient(135deg, #13202b 0%, #164e63 100%);
    color: white;
    padding: 24px 28px;
    border-radius: 14px;
    box-shadow: 0 18px 42px rgba(19, 32, 43, .16);
    margin-bottom: 1rem;
  }
  .hero-shell h1 {
    margin: 0 0 .35rem;
    font-size: 2.05rem;
    line-height: 1.05;
    letter-spacing: 0;
  }
  .hero-shell p {
    margin: 0;
    max-width: 860px;
    color: rgba(255,255,255,.82);
    font-size: 1.02rem;
  }
  .hero-badges {
    display: flex;
    gap: .5rem;
    flex-wrap: wrap;
    margin-top: 1rem;
  }
  .hero-badge {
    border: 1px solid rgba(255,255,255,.18);
    background: rgba(255,255,255,.10);
    border-radius: 8px;
    padding: .28rem .72rem;
    font-size: .78rem;
  }
  .section-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1rem 1.15rem;
    box-shadow: 0 8px 24px rgba(20, 39, 55, .05);
    margin-bottom: .85rem;
    color: var(--ink);
  }
  .section-card:empty {
    display: none;
  }
  .section-card h1,
  .section-card h2,
  .section-card h3,
  .section-card p,
  .section-card li,
  .section-card span {
    color: var(--ink);
  }
  .mini-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .85rem;
    margin: 1rem 0 0;
  }
  .mini-card {
    background: rgba(255,255,255,.12);
    border: 1px solid rgba(255,255,255,.14);
    border-radius: 10px;
    padding: .9rem 1rem;
  }
  .mini-card .label {
    font-size: .75rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: rgba(255,255,255,.68);
    margin-bottom: .3rem;
  }
  .mini-card .value {
    font-size: 1.28rem;
    font-weight: 700;
  }
  div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: .8rem 1rem;
    box-shadow: 0 8px 20px rgba(20, 39, 55, .04);
  }
  div[data-testid="stMetric"] * {
    color: var(--ink) !important;
  }
  div[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
  }
  div[data-testid="stMetricValue"] {
    color: var(--ink) !important;
  }
  div[data-testid="stMetricDelta"] {
    color: #16a34a !important;
  }
  div[data-testid="stMetricDelta"] * {
    color: #16a34a !important;
  }
  .stTabs [data-baseweb="tab-list"] {
    gap: .35rem;
  }
  .stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,.62);
    border: 1px solid var(--line);
    border-radius: 8px;
    height: 42px;
    padding: 0 1rem;
  }
  .stTabs [data-baseweb="tab"] p {
    color: var(--ink);
  }
  .stTabs [aria-selected="true"] {
    background: #155e75;
    color: white;
    border-color: transparent;
  }
  .stTabs [aria-selected="true"] p {
    color: white;
  }
  .reference-list {
    margin: .35rem 0 0;
    padding-left: 1.1rem;
    color: var(--muted);
    font-size: .92rem;
  }
  .status-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: .16rem .55rem;
    font-size: .76rem;
    font-weight: 700;
  }
  .status-ok { background: #dcfce7; color: var(--ok); }
  .status-warn { background: #fef3c7; color: var(--warn); }
  .status-ko { background: #fee2e2; color: var(--bad); }
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h3,
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] li {
    color: var(--ink);
  }
  [data-testid="stCaptionContainer"],
  [data-testid="stCaptionContainer"] * {
    color: var(--muted) !important;
  }
  .hero-shell h1,
  .hero-shell p,
  .hero-badge,
  .hero-badge * {
    color: white !important;
  }
</style>
"""


def render_status(label: str, value: float, limit: float, inverse: bool = False) -> None:
    if inverse:
        ok = value <= limit
        state = "OK" if ok else "ALTO"
        delta = value - limit
    else:
        ok = value >= limit
        state = "OK" if ok else "KO"
        delta = value - limit
    st.metric(label, f"{value:.2f}", delta=f"{state} ({delta:+.2f})")


def governing_combination(results: dict, key: str, lower_is_worse: bool = True) -> tuple[str, float]:
    candidates = {
        "Statica GEO": results["statico"][key],
        "Statica EQU": results["st_EQU"].get(key, results["statico"][key]),
        "Sismica kv+": results["sismico"][key],
        "Sismica kv-": results["se_neg"][key],
    }
    if lower_is_worse:
        name = min(candidates, key=candidates.get)
    else:
        name = max(candidates, key=candidates.get)
    return name, candidates[name]


def status_label(value: float, limit: float, inverse: bool = False) -> str:
    ok = value <= limit if inverse else value >= limit
    return "Verificato" if ok else "Non verificato"


def verification_overview(dati: DatiMuro, results: dict, pendio: dict | None) -> list[dict]:
    rows = [
        {
            "Verifica": "Ribaltamento statico",
            "Combinazione": "EQU",
            "Valore": results["st_EQU"]["FS_rib"],
            "Limite": 1.0,
            "Esito": status_label(results["st_EQU"]["FS_rib"], 1.0),
        },
        {
            "Verifica": "Scorrimento statico",
            "Combinazione": "GEO",
            "Valore": results["statico"]["FS_scorr"],
            "Limite": 1.0,
            "Esito": status_label(results["statico"]["FS_scorr"], 1.0),
        },
        {
            "Verifica": "Portanza statica",
            "Combinazione": "GEO",
            "Valore": results["statico"]["FS_portanza"],
            "Limite": 1.0,
            "Esito": status_label(results["statico"]["FS_portanza"], 1.0),
        },
        {
            "Verifica": "Pressione ammissibile",
            "Combinazione": "GEO",
            "Valore": results["statico"]["qmax"] / max(dati.q_amm, 1e-9),
            "Limite": 1.0,
            "Esito": status_label(results["statico"]["qmax"] / max(dati.q_amm, 1e-9), 1.0, inverse=True),
        },
        {
            "Verifica": "Portanza sismica",
            "Combinazione": "kh, kv+",
            "Valore": results["sismico"]["FS_portanza"],
            "Limite": 1.0,
            "Esito": status_label(results["sismico"]["FS_portanza"], 1.0),
        },
    ]
    if pendio and pendio.get("statico"):
        rows.append(
            {
                "Verifica": "Stabilita globale pendio",
                "Combinazione": "Statico",
                "Valore": pendio["statico"]["FS"],
                "Limite": 1.30,
                "Esito": status_label(pendio["statico"]["FS"], 1.30),
            }
        )
    return rows


st.set_page_config(page_title="Muro di sostegno NTC", layout="wide")
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <section class="hero-shell">
      <h1>Muro di sostegno</h1>
      <p>Relazione di calcolo geotecnica con sintesi degli SLU, combinazioni governanti, pressioni di contatto e verifica globale del pendio.</p>
      <div class="hero-badges">
        <span class="hero-badge">NTC 2018</span>
        <span class="hero-badge">Circolare 2019</span>
        <span class="hero-badge">EC7</span>
        <span class="hero-badge">SLU GEO / EQU</span>
      </div>
      <div class="mini-grid">
        <div class="mini-card">
          <div class="label">Quadro verifiche</div>
          <div class="value">GEO + EQU</div>
        </div>
        <div class="mini-card">
          <div class="label">Report</div>
          <div class="value">Word + PDF</div>
        </div>
        <div class="mini-card">
          <div class="label">Controlli</div>
          <div class="value">Dati + esiti</div>
        </div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Import / Export input")
    uploaded_input = st.file_uploader("Reimporta input JSON", type=["json"], key="muro_json")
    defaults = DEFAULTS.copy()
    if uploaded_input is not None:
        try:
            defaults.update(json.load(uploaded_input))
            st.success("Input importati correttamente.")
        except Exception:
            st.error("JSON non valido.")

    st.header("Geometria del muro")
    H = st.number_input("Altezza terreno H [m]", 0.5, 20.0, float(defaults["H"]), 0.1)
    B = st.number_input("Base totale B [m]", 0.5, 20.0, float(defaults["B"]), 0.1)
    B_punta = st.number_input("Punta [m]", 0.1, 10.0, float(defaults["B_punta"]), 0.1)
    B_tallone = st.number_input("Tallone [m]", 0.1, 15.0, float(defaults["B_tallone"]), 0.1)
    t_base = st.number_input("Spessore base [m]", 0.1, 5.0, float(defaults["t_base"]), 0.05)
    t_fusto_top = st.number_input("Spessore fusto in testa [m]", 0.1, 3.0, float(defaults["t_fusto_top"]), 0.05)
    t_fusto_bot = st.number_input("Spessore fusto al piede [m]", 0.1, 5.0, float(defaults["t_fusto_bot"]), 0.05)
    h_fronte = st.number_input("Altezza terreno a fronte [m]", 0.0, 10.0, float(defaults["h_fronte"]), 0.1)
    include_passivo = st.checkbox("Considera contributo passivo", value=bool(defaults["include_passivo"]))

    st.header("Carichi e verifiche")
    q = st.number_input("Sovraccarico q [kPa]", 0.0, 100.0, float(defaults["q"]), 1.0)
    gamma_cls = st.number_input("Peso di volume cls [kN/m3]", 20.0, 28.0, float(defaults["gamma_cls"]), 0.5)
    mu_base = st.number_input("Coefficiente attrito base mu [-]", 0.0, 1.2, float(defaults["mu_base"]), 0.05)
    delta_muro = st.number_input("Attrito Terra-Muro delta [deg]", 0.0, 45.0, float(defaults["delta_muro"]), 1.0)
    q_amm = st.number_input("q ammissibile di riferimento [kPa]", 50.0, 1000.0, float(defaults["q_amm"]), 10.0)

    st.header("Ancoraggi")
    ha_tirante = st.checkbox("Inserisci tirante di ancoraggio", value=bool(defaults["ha_tirante"]))
    if ha_tirante:
        t_quota = st.number_input("Quota applicazione dal fondo scavo [m]", 0.0, float(H + t_base), float(defaults["t_quota"]), 0.1)
        t_tiro = st.number_input("Tiro di progetto [kN/m]", 0.0, 1000.0, float(defaults["t_tiro"]), 10.0)
        t_inclinazione = st.number_input("Inclinazione rispetto all'orizzontale [deg]", 0.0, 60.0, float(defaults["t_inclinazione"]), 1.0)
    else:
        t_quota, t_tiro, t_inclinazione = 0.0, 0.0, 0.0

    st.header("Sismica pseudo-statica")
    kh = st.number_input("kh [-]", 0.0, 1.0, float(defaults["kh"]), 0.01)
    kv = st.number_input("kv [-]", 0.0, 1.0, float(defaults["kv"]), 0.01)

    st.header("Falda")
    falda_retro = st.number_input("Profondita falda a tergo [m]", 0.0, 100.0, float(defaults["falda_retro"]), 0.1)
    falda_fronte = st.number_input("Profondita falda a fronte [m]", 0.0, 100.0, float(defaults["falda_fronte"]), 0.1)

    st.header("Stratigrafia")
    st.caption("Righe: spessore,gamma_dry,gamma_sat,phi,cu,k")
    stratigrafia_csv = st.text_area("Stratigrafia", value=str(defaults["stratigrafia_csv"]), height=150)

    st.header("Pendio")
    analizza_pendio = st.checkbox("Esegui verifica pendio", value=bool(defaults["analizza_pendio"]))
    if analizza_pendio:
        pendio_H = st.number_input("Altezza pendio [m]", 1.0, 30.0, float(defaults["pendio_H"]), 0.25)
        pendio_beta = st.number_input("Inclinazione pendio [deg]", 10.0, 79.0, float(defaults["pendio_beta"]), 1.0)
        pendio_berma = st.number_input("Berma di monte [m]", 1.0, 30.0, float(defaults["pendio_berma"]), 0.25)
    else:
        pendio_H = float(defaults["pendio_H"])
        pendio_beta = float(defaults["pendio_beta"])
        pendio_berma = float(defaults["pendio_berma"])

dati = DatiMuro(
    H=H,
    q=q,
    gamma_cls=gamma_cls,
    B=B,
    B_punta=B_punta,
    B_tallone=B_tallone,
    t_base=t_base,
    t_fusto_top=t_fusto_top,
    t_fusto_bot=t_fusto_bot,
    mu_base=mu_base,
    q_amm=q_amm,
    h_fronte=h_fronte,
    falda_retro=falda_retro,
    falda_fronte=falda_fronte,
    kh=kh,
    kv=kv,
    delta_muro=delta_muro,
    include_passivo=include_passivo,
    stratigrafia_csv=stratigrafia_csv,
    ha_tirante=ha_tirante,
    t_quota=t_quota,
    t_inclinazione=t_inclinazione,
    t_tiro=t_tiro,
    analizza_pendio=analizza_pendio,
    pendio_H=pendio_H,
    pendio_beta=pendio_beta,
    pendio_berma=pendio_berma,
)

errors = valida_dati(dati)
if errors:
    for error in errors:
        st.error(error)
    st.stop()

results = calcola_muro(dati)
summary_df = tabella_sintesi(dati, results)
sollecitazioni_df = tabella_sollecitazioni(results)
current_input = dict(dati.__dict__)
governing_fs_name, governing_fs_value = governing_combination(results, "FS_portanza")
governing_q_name, governing_q_value = governing_combination(results, "qmax", lower_is_worse=False)
pendio = analisi_stabilita_pendio(dati, results["stratigrafia"]) if dati.analizza_pendio else None
warnings = genera_warning(dati, results)
notes = genera_note(dati, results)
overview_rows = verification_overview(dati, results, pendio)

with st.sidebar:
    st.divider()
    st.subheader("Relazioni")
    report_data = {
        "H": dati.H,
        "q": dati.q,
        "gamma_cls": dati.gamma_cls,
        "B": dati.B,
        "B_punta": dati.B_punta,
        "B_tallone": dati.B_tallone,
        "t_base": dati.t_base,
        "t_fusto_top": dati.t_fusto_top,
        "t_fusto_bot": dati.t_fusto_bot,
        "mu_base": dati.mu_base,
        "q_amm": dati.q_amm,
        "h_fronte": dati.h_fronte,
        "falda_retro": dati.falda_retro,
        "falda_fronte": dati.falda_fronte,
        "kh": dati.kh,
        "kv": dati.kv,
        "delta_muro": dati.delta_muro,
        "ha_tirante": dati.ha_tirante,
        "t_quota": dati.t_quota,
        "t_inclinazione": dati.t_inclinazione,
        "t_tiro": dati.t_tiro,
        "include_passivo": dati.include_passivo,
        "stratigrafia_csv": dati.stratigrafia_csv,
        "pendio": pendio,
        "warnings": warnings,
        "notes": notes,
        "risultati": results,
    }
    try:
        word_bytes = create_word_report(report_data)
        st.download_button(
            label="Scarica relazione Word",
            data=word_bytes,
            file_name="Relazione_Muro_Sostegno.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"Errore Word: {exc}")
    try:
        pdf_bytes = create_pdf_report(report_data)
        st.download_button(
            label="Scarica relazione PDF",
            data=pdf_bytes,
            file_name="Relazione_Muro_Sostegno.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as exc:
        st.warning(f"Export PDF non disponibile: {exc}")
    st.download_button(
        label="Esporta input JSON",
        data=export_json(current_input),
        file_name="input_muro.json",
        mime="application/json",
        use_container_width=True,
    )

metric_col_1, metric_col_2, metric_col_3, metric_col_4, metric_col_5 = st.columns(5)
with metric_col_1:
    render_status("FS Ribaltamento", results["st_EQU"]["FS_rib"], 1.0)
with metric_col_2:
    render_status("FS Scorrimento", results["statico"]["FS_scorr"], 1.0)
with metric_col_3:
    render_status("FS Portanza", results["statico"]["FS_portanza"], 1.0)
with metric_col_4:
    render_status("q_max / q_amm", results["statico"]["qmax"] / dati.q_amm, 1.0, inverse=True)
with metric_col_5:
    if pendio and pendio["statico"]:
        render_status("FS Pendio", pendio["statico"]["FS"], 1.30)
    else:
        st.metric("FS Pendio", "n.d.", delta="attiva modulo")

tabs = st.tabs(
    [
        "Sintesi tecnica",
        "Modello e verifiche",
        "Output pressioni",
        "Analisi strutturale",
        "Stabilita pendio",
        "Report e controlli",
        "Note",
    ]
)

with tabs[0]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Sintesi per relazione")
    intro_left, intro_right = st.columns([1.35, 1.0])
    with intro_left:
        st.dataframe(overview_rows, use_container_width=True, hide_index=True)
    with intro_right:
        st.markdown("**Riferimenti assunti nel controllo**")
        st.markdown(
            "<ul class='reference-list'>"
            + "".join(f"<li>{ref}</li>" for ref in DESIGN_REFERENCES)
            + "</ul>",
            unsafe_allow_html=True,
        )
        st.divider()
        if warnings:
            st.error(f"{len(warnings)} criticita automatica da esaminare prima dell'uso progettuale.")
        else:
            st.success("Nessuna criticita automatica nelle verifiche principali.")
        st.caption("Il modello resta uno strumento di supporto: il giudizio tecnico e la caratterizzazione geotecnica rimangono responsabilita del progettista.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Combinazioni governanti")
    g1, g2, g3 = st.columns(3)
    with g1:
        render_status("Portanza minima", governing_fs_value, 1.0)
        st.caption(f"Governante: {governing_fs_name}")
    with g2:
        render_status("q_max / q_amm", governing_q_value / dati.q_amm, 1.0, inverse=True)
        st.caption(f"Governante: {governing_q_name}")
    with g3:
        if pendio and pendio["statico"]:
            render_status("Pendio statico", pendio["statico"]["FS"], 1.30)
        else:
            st.metric("Pendio statico", "n.d.")
        st.caption("Limite indicativo usato nel cruscotto: FS >= 1.30")
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[1]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Modello di calcolo")
    left, right = st.columns([1.85, 1.0])
    with left:
        st.plotly_chart(figura_geometria(dati), use_container_width=True)
    with right:
        st.dataframe(results["stratigrafia"], use_container_width=True, height=420)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Verifiche geotecniche")
    st.dataframe(summary_df, use_container_width=True)
    info_1, info_2 = st.columns(2)
    with info_1:
        if governing_fs_value < 1.0:
            st.error(f"La combinazione governante per la portanza e {governing_fs_name} con FS = {governing_fs_value:.2f}.")
        else:
            st.success(f"La portanza resta verificata anche nella combinazione piu gravosa: {governing_fs_name} con FS = {governing_fs_value:.2f}.")
    with info_2:
        st.info(f"q_max governante: {governing_q_value:.1f} kPa in {governing_q_name}.")
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[2]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Pressioni sul terreno")
    st.plotly_chart(figura_output(results), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[3]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Sollecitazioni strutturali allo spiccato")
    st.markdown(
        "Valori utili per il dimensionamento del fusto alla quota `y = t_base`. "
        "I segni sono mantenuti per una lettura tecnica coerente."
    )
    st.dataframe(sollecitazioni_df, use_container_width=True)
    st.divider()
    st.subheader("Effetto del tirante")
    if dati.ha_tirante:
        st.success("Tirante attivo nel modello.")
        st.markdown(
            f"- Tiro di progetto: **{dati.t_tiro:.1f} kN/m**\n"
            f"- Quota di applicazione: **{dati.t_quota:.2f} m**\n"
            f"- Inclinazione: **{dati.t_inclinazione:.1f} deg**"
        )
    else:
        st.info("Nessun tirante inserito. Il modello considera il solo muro a mensola.")
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[4]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Verifica di stabilita del pendio")
    if not pendio or not pendio["statico"]:
        st.warning("Non e stato possibile individuare una superficie critica valida con i parametri correnti.")
    else:
        a, b, c = st.columns(3)
        with a:
            render_status("FS statico pendio", pendio["statico"]["FS"], 1.30)
        with b:
            if pendio["sismico"]:
                render_status("FS sismico pendio", pendio["sismico"]["FS"], 1.10)
            else:
                st.metric("FS sismico pendio", "n.d.")
        with c:
            props = pendio["props"]
            st.metric("phi equivalente", f"{props['phi_deg']:.1f} deg", delta=f"cu {props['cu_kPa']:.1f} kPa")

        st.plotly_chart(figura_pendio(dati, pendio), use_container_width=True)

        summary_left, summary_right = st.columns([1.2, 1.0])
        with summary_left:
            st.markdown(
                f"""
                **Ipotesi di calcolo**

                - Metodo: Fellenius semplificato con ricerca automatica del cerchio critico
                - Pendio: `H = {dati.pendio_H:.2f} m`, `beta = {dati.pendio_beta:.1f} deg`
                - Berma di monte: `{dati.pendio_berma:.2f} m`
                - Coefficiente sismico usato nel pendio: `kh = {dati.kh:.2f}`
                """
            )
        with summary_right:
            st.dataframe(
                pendio["statico"]["slices"][["x", "alpha_deg", "W", "S_res", "S_drive"]].round(2),
                use_container_width=True,
                height=280,
            )
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[5]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Controlli di progetto")
    st.dataframe(summary_df.copy(), use_container_width=True)
    st.write(f"q_amm inserita: **{dati.q_amm:.1f} kPa**")
    st.write(f"q_max governante: **{governing_q_value:.1f} kPa** in **{governing_q_name}**")
    if governing_q_value > dati.q_amm:
        st.error("La pressione massima supera la q ammissibile di riferimento inserita.")
    else:
        st.success("La pressione massima resta entro la q ammissibile di riferimento.")
    if pendio and pendio["statico"]:
        if pendio["statico"]["FS"] < 1.30:
            st.warning("Il pendio risulta critico in campo statico per il cerchio governante individuato.")
        else:
            st.success("Il pendio risulta verificato in campo statico con il modello adottato.")
    st.info(
        "L'export PDF richiede il pacchetto `fpdf2`. Se non installato, l'app continua a funzionare "
        "e mantiene disponibile l'export Word."
    )
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[6]:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    if pendio and pendio["statico"]:
        notes.append(f"FS statico pendio: {pendio['statico']['FS']:.2f}.")
    if pendio and pendio["sismico"]:
        notes.append(f"FS sismico pendio: {pendio['sismico']['FS']:.2f}.")

    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("Nessuna criticita automatica rilevata nelle verifiche principali.")
    for note in notes:
        st.info(note)
    st.markdown('</div>', unsafe_allow_html=True)
