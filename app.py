# -*- coding: utf-8 -*-
import json
import streamlit as st
from src import (
    DatiMuro, DEFAULT_STRAT,
    valida_dati, calcola_muro, tabella_sintesi, tabella_sollecitazioni,
    figura_geometria, figura_output, export_json,
    genera_warning, genera_note,
)

DEFAULTS = {
    'H': 5.0, 'q': 10.0, 'gamma_cls': 24.0,
    'B': 3.5, 'B_punta': 1.0, 'B_tallone': 2.5,
    't_base': 0.5, 't_fusto_top': 0.30, 't_fusto_bot': 0.50,
    'mu_base': 0.55, 'q_amm': 250.0,
    'h_fronte': 0.5, 'falda_retro': 99.0, 'falda_fronte': 99.0,
    'kh': 0.15, 'kv': 0.05, 'delta_muro': 20.0,
    'include_passivo': True,
    'stratigrafia_csv': DEFAULT_STRAT,
    'ha_tirante': False,
    't_quota': 4.0,
    't_inclinazione': 15.0,
    't_tiro': 150.0
}

st.set_page_config(page_title='Muro di sostegno NTC', layout='wide')
st.title('Muro - Analisi Avanzata NTC 2008 / MAX')
st.caption('Logica geotecnica e strutturale. Inclusione Tiranti e Sollecitazioni.')

# ---------------------------------------------------------------------------
# Sidebar: input
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header('Import / Export input')
    up = st.file_uploader('Reimporta input JSON', type=['json'], key='muro_json')
    defaults = DEFAULTS.copy()
    if up is not None:
        try:
            defaults.update(json.load(up))
            st.success('Input importati.')
        except Exception:
            st.error('JSON non valido.')

    st.header('Geometria')
    H = st.number_input('Altezza terreno H [m]', 0.5, 20.0, float(defaults['H']), 0.1)
    B = st.number_input('Base totale B [m]', 0.5, 20.0, float(defaults['B']), 0.1)
    B_punta = st.number_input('Punta [m]', 0.1, 10.0, float(defaults['B_punta']), 0.1)
    B_tallone = st.number_input('Tallone [m]', 0.1, 15.0, float(defaults['B_tallone']), 0.1)
    t_base = st.number_input('Spessore base [m]', 0.1, 5.0, float(defaults['t_base']), 0.05)
    t_fusto_top = st.number_input('Spessore fusto in testa [m]', 0.1, 3.0, float(defaults['t_fusto_top']), 0.05)
    t_fusto_bot = st.number_input('Spessore fusto al piede [m]', 0.1, 5.0, float(defaults['t_fusto_bot']), 0.05)
    h_fronte = st.number_input('Altezza terreno a fronte [m]', 0.0, 10.0, float(defaults['h_fronte']), 0.1)
    include_passivo = st.checkbox('Considera contributo passivo', value=bool(defaults['include_passivo']))

    st.header('Carichi e verifiche')
    q = st.number_input('Sovraccarico q [kPa]', 0.0, 100.0, float(defaults['q']), 1.0)
    gamma_cls = st.number_input('Peso di volume cls [kN/m³]', 20.0, 28.0, float(defaults['gamma_cls']), 0.5)
    mu_base = st.number_input('Coefficiente attrito base μ [-]', 0.0, 1.2, float(defaults['mu_base']), 0.05)
    delta_muro = st.number_input('Attrito Terra-Muro δ [°]', 0.0, 45.0, float(defaults['delta_muro']), 1.0)
    q_amm = st.number_input('q ammissibile (riferimento) [kPa]', 50.0, 1000.0, float(defaults['q_amm']), 10.0)

    st.header('Ancoraggi (Tiranti)')
    ha_tirante = st.checkbox('Inserisci Tirante di ancoraggio', value=bool(defaults['ha_tirante']))
    if ha_tirante:
        t_quota = st.number_input('Quota applicazione (dal fondo scavo) [m]', 0.0, float(H + t_base), float(defaults['t_quota']), 0.1)
        t_tiro = st.number_input('Tiro di progetto (per m lineare) [kN/m]', 0.0, 1000.0, float(defaults['t_tiro']), 10.0)
        t_inclinazione = st.number_input('Inclinazione rispetto orizzontale [°]', 0.0, 60.0, float(defaults['t_inclinazione']), 1.0)
    else:
        t_quota, t_tiro, t_inclinazione = 0.0, 0.0, 0.0

    st.header('Sismica pseudo-statica')
    kh = st.number_input('kh [-]', 0.0, 1.0, float(defaults['kh']), 0.01)
    kv = st.number_input('kv [-]', 0.0, 1.0, float(defaults['kv']), 0.01)

    st.header('Falda')
    falda_retro = st.number_input('Profondità falda a tergo [m]', 0.0, 100.0, float(defaults['falda_retro']), 0.1)
    falda_fronte = st.number_input('Profondità falda a fronte [m]', 0.0, 100.0, float(defaults['falda_fronte']), 0.1)

    st.header('Stratigrafia')
    st.caption('Righe: spessore,gamma_dry,gamma_sat,phi,cu,k')
    stratigrafia_csv = st.text_area('Stratigrafia', value=str(defaults['stratigrafia_csv']), height=150)

# ---------------------------------------------------------------------------
# Calcolo
# ---------------------------------------------------------------------------
d = DatiMuro(
    H=H, q=q, gamma_cls=gamma_cls, B=B, B_punta=B_punta, B_tallone=B_tallone,
    t_base=t_base, t_fusto_top=t_fusto_top, t_fusto_bot=t_fusto_bot,
    mu_base=mu_base, q_amm=q_amm, h_fronte=h_fronte, falda_retro=falda_retro, falda_fronte=falda_fronte,
    kh=kh, kv=kv, delta_muro=delta_muro, include_passivo=include_passivo, stratigrafia_csv=stratigrafia_csv,
    ha_tirante=ha_tirante, t_quota=t_quota, t_inclinazione=t_inclinazione, t_tiro=t_tiro
)

err = valida_dati(d)
if err:
    for e in err: st.error(e)
    st.stop()

r = calcola_muro(d)
df_sintesi = tabella_sintesi(d, r)
current = {k: v for k, v in d.__dict__.items()}

# ---------------------------------------------------------------------------
# Metriche principali
# ---------------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric('FS Ribaltamento', f"{r['st_EQU']['FS_rib']:.2f}")
c2.metric('FS Scorrimento', f"{r['statico']['FS_scorr']:.2f}")

qmax_val = r['statico']['qmax']
c3.metric('q_max [kPa]', f"{qmax_val:.1f}")

q_lim_val = r['statico']['q_lim']
c4.metric('q_lim (Hansen)', f"{q_lim_val:.1f}")

fs_port = r['statico']['FS_portanza']
c5.metric('FS Portanza', f"{fs_port:.2f}", delta="OK" if fs_port >= 1.0 else "NO", delta_color="normal" if fs_port >= 1.0 else "inverse")

# ---------------------------------------------------------------------------
# Tab
# ---------------------------------------------------------------------------
t1, t2, t3, t4, t5 = st.tabs([
    '📐 Cruscotto Globale', '📊 Output Pressioni', '🔗 Analisi Strutturale e Tiranti', '🌍 Stabilità Pendio', '⚠️ Note'
])

with t1:
    st.subheader('Modello di Calcolo')
    col_plot, col_df = st.columns([2, 1])
    with col_plot:
        st.plotly_chart(figura_geometria(d), use_container_width=True)
    with col_df:
        st.dataframe(r['stratigrafia'], use_container_width=True)

    st.divider()
    st.subheader('Verifiche Geotecniche (Sintesi)')
    st.dataframe(df_sintesi, use_container_width=True)

with t2:
    st.subheader("Pressioni sul terreno")
    st.plotly_chart(figura_output(r), use_container_width=True)

with t3:
    st.header("Sollecitazioni Strutturali allo Spiccato")
    st.markdown("Valori calcolati per il dimensionamento delle armature alla base del fusto (quota $y = t_{base}$). I valori includono il peso proprio del fusto, le inerzie sismiche, la spinta delle terre e l'eventuale ancoraggio.")
    
    df_sollec = tabella_sollecitazioni(r)
    st.dataframe(df_sollec, use_container_width=True)

    st.divider()
    st.subheader("Effetto del Tirante di Ancoraggio")
    if d.ha_tirante:
        st.success("Tirante attivo. L'equilibrio strutturale beneficia del pretiro.")
        st.markdown(f"""
        - Tiro di progetto: **{d.t_tiro} kN/m**
        - Quota: **{d.t_quota} m**
        - Il momento flettente allo spiccato si è ridotto grazie al momento stabilizzante del tirante.
        """)
    else:
        st.info("Nessun tirante inserito. Spunta la voce nella sidebar per valutare le riduzioni di Taglio e Momento flettente sul fusto.")

with t4:
    st.header("Stabilità Globale del Pendio")
    st.info("🚧 Modulo in fase di espansione: Ricerca del cerchio di scivolamento critico (Metodo di Fellenius/Bishop).")

with t5:
    warnings = genera_warning(d, r)
    for w in warnings: st.warning(w)
    note = genera_note(d, r)
    for n in note: st.info(n)
