# -*- coding: utf-8 -*-
import json
import streamlit as st
from src import (
    DatiMuro, DEFAULT_STRAT,
    valida_dati, calcola_muro, tabella_sintesi,
    figura_geometria, figura_output, export_json,
    genera_warning, genera_note,
)

DEFAULTS = {
    'H': 5.0, 'q': 10.0, 'gamma_cls': 24.0,
    'B': 3.5, 'B_punta': 1.0, 'B_tallone': 2.0,
    't_base': 0.5, 't_fusto_top': 0.30, 't_fusto_bot': 0.50,
    'mu_base': 0.55, 'q_amm': 250.0,
    'h_fronte': 0.5, 'falda_retro': 99.0, 'falda_fronte': 99.0,
    'kh': 0.15, 'kv': 0.05, 'delta_muro': 20.0,
    'include_passivo': True,
    'stratigrafia_csv': DEFAULT_STRAT,
}

st.set_page_config(page_title='Muro di sostegno NTC', layout='wide')
st.title('Muro - Analisi Avanzata NTC 2008 / MAX')
st.caption('Logica geotecnica aggiornata agli stati limite EQU/GEO. Mantenuti export e visualizzazioni originali.')

# ---------------------------------------------------------------------------
# Sidebar: input (Tutti i tuoi controlli originali)
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
    q_amm = st.number_input('q ammissibile [kPa]', 50.0, 1000.0, float(defaults['q_amm']), 10.0)

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
    H, q, gamma_cls, B, B_punta, B_tallone,
    t_base, t_fusto_top, t_fusto_bot,
    mu_base, q_amm,
    h_fronte, falda_retro, falda_fronte,
    kh, kv, delta_muro, include_passivo, stratigrafia_csv,
)
err = valida_dati(d)
if err:
    for e in err:
        st.error(e)
    st.stop()

r = calcola_muro(d)
df_sintesi = tabella_sintesi(d, r)
current = {k: v for k, v in d.__dict__.items()}

# ---------------------------------------------------------------------------
# Metriche principali (Le tue 6 colonne originali!)
# ---------------------------------------------------------------------------
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric('FS rib. statico (EQU)',   f"{r['st_EQU']['FS_rib']:.2f}")
c2.metric('FS scorr. statico (GEO)', f"{r['statico']['FS_scorr']:.2f}")
c3.metric('FS rib. sismico',   f"{r['sismico']['FS_rib']:.2f}")
c4.metric('FS scorr. sismico', f"{r['sismico']['FS_scorr']:.2f}")

qmax_val = r['statico']['qmax']
delta_q = qmax_val - d.q_amm
c5.metric(
    'qmax GEO [kPa]',
    f"{qmax_val:.1f}",
    delta=f"{delta_q:+.1f} vs q_amm",
    delta_color='inverse',
)
c6.metric('q_amm [kPa]', f"{d.q_amm:.1f}")

# ---------------------------------------------------------------------------
# Le tue Tab Originali
# ---------------------------------------------------------------------------
t1, t2, t3, t4, t5 = st.tabs([
    'Sintesi e Download', 'Stratigrafia', 'Geometria Plotly', 'Output Plotly', 'Note e Warning NTC',
])

with t1:
    st.subheader('Tabella di sintesi')
    st.dataframe(df_sintesi, use_container_width=True)

    st.subheader('Download')
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.download_button('Salva input JSON', export_json(current), 'muro_input.json', 'application/json')
    with col_b:
        st.download_button('Sintesi CSV (statico)', df_sintesi[['Parametro', 'Statico (GEO/EQU)']].to_csv(index=False).encode('utf-8'), 'muro_sintesi_statico.csv', 'text/csv')
    with col_c:
        st.download_button('Sintesi CSV (sismico)', df_sintesi[['Parametro', 'Sismico kv+']].to_csv(index=False).encode('utf-8'), 'muro_sintesi_sismico.csv', 'text/csv')
    with col_d:
        st.download_button('Sintesi CSV (completa)', df_sintesi.to_csv(index=False).encode('utf-8'), 'muro_sintesi.csv', 'text/csv')

with t2:
    st.dataframe(r['stratigrafia'], use_container_width=True)

with t3:
    st.plotly_chart(figura_geometria(d), use_container_width=True)

with t4:
    st.plotly_chart(figura_output(r), use_container_width=True)

with t5:
    st.subheader('Warning tecnici')
    warnings = genera_warning(d, r)
    if warnings:
        for w in warnings:
            st.warning(w)
    else:
        st.success('Nessun warning: tutte le verifiche NTC sono soddisfatte.')

    st.subheader('Note automatiche')
    note = genera_note(d, r)
    if note:
        for n in note:
            st.info(n)

    st.subheader('Nuove Ipotesi di calcolo NTC (MAX)')
    st.markdown("""
**Metodo di calcolo adottato (Aggiornato)**
- **Spinta attiva (Mononobe-Okabe):** A differenza del calcolo originale (Rankine), ora viene impiegato l'approccio di Coulomb / Mononobe-Okabe, che consente di considerare la componente di attrito terra-muro `δ`.
- **Combinazioni NTC 2008/2018:** La valutazione viene scissa rigorosamente fra Stato Limite EQU (Ribaltamento, con massimizzazione delle spinte) e Stato Limite GEO (Scorrimento e Capacità Portante).
- **Forze d'inerzia:** Nel calcolo dei momenti destabilizzanti sismici e negli sforzi di taglio alla base sono ora incluse esplicitamente le masse del fusto, della fondazione e della "zavorra" (terreno sopra il tallone), come indicato nei manuali del software MAX.
    """)
