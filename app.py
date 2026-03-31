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
st.caption('Logica geotecnica aggiornata agli stati limite EQU/GEO. Calcolo Rigoroso Capacità Portante e Tiranti.')

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
    t_tiro=t_tiro
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
# Metriche principali (Layout a 5 colonne, per non avere errori di variabili non definite)
# ---------------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric('FS Ribaltamento (EQU)', f"{r['st_EQU']['FS_rib']:.2f}")
c2.metric('FS Scorrimento (GEO)', f"{r['statico']['FS_scorr']:.2f}")

qmax_val = r['statico']['qmax']
c3.metric('q_max [kPa]', f"{qmax_val:.1f}")

q_lim_val = r['statico']['q_lim']
c4.metric('q_lim (Hansen) [kPa]', f"{q_lim_val:.1f}")

fs_port = r['statico']['FS_portanza']
c5.metric(
    'FS Portanza',
    f"{fs_port:.2f}",
    delta="Soddisfatto" if fs_port >= 1.0 else "Non Soddisfatto",
    delta_color="normal" if fs_port >= 1.0 else "inverse"
)

# ---------------------------------------------------------------------------
# Tab
# ---------------------------------------------------------------------------
t1, t2, t3, t4, t5 = st.tabs([
    '📐 Modello e Sintesi (Cruscotto)', 
    '📊 Output Plotly (Pressioni)', 
    '🔗 Analisi Tiranti', 
    '🌍 Stabilità Globale Pendio', 
    '⚠️ Warning e Note NTC'
])

with t1:
    st.subheader('Geometria e Stratigrafia di calcolo')
    col_plot, col_df = st.columns([2, 1])
    with col_plot:
        st.plotly_chart(figura_geometria(d), use_container_width=True)
    with col_df:
        st.markdown("**Stratigrafia impostata**")
        st.dataframe(r['stratigrafia'], use_container_width=True)

    st.divider()

    st.subheader('Tabella di Sintesi')
    st.dataframe(df_sintesi, use_container_width=True)

    st.markdown("**Download Output**")
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
    st.subheader("Diagramma delle pressioni")
    st.plotly_chart(figura_output(r), use_container_width=True)

with t3:
    st.header("Effetto dei Tiranti di Ancoraggio")
    if d.ha_tirante:
        st.success("Tirante di ancoraggio attivo nel calcolo.")
        st.markdown(f"""
        **Dati di progetto:**
        - Tiro (T): **{d.t_tiro} kN/m**
        - Quota di applicazione: **{d.t_quota} m** dal fondo base
        - Inclinazione: **{d.t_inclinazione}°** verso il basso

        **Azioni stabilizzanti introdotte:**
        Il tirante introduce una componente orizzontale che si oppone allo scorrimento, una componente verticale che incrementa lo sforzo normale (e quindi l'attrito di base) e un momento stabilizzante che contrasta il ribaltamento.
        """)
    else:
        st.info("Nessun tirante inserito. Spunta 'Inserisci Tirante di ancoraggio' nella barra laterale per valutare l'aumento della stabilità globale.")

with t4:
    st.header("Analisi di Stabilità Globale")
    st.markdown("Questa sezione implementerà la ricerca del cerchio di scivolamento critico che coinvolge il sistema terreno-muro.")
    st.info("🚧 Modulo in fase di espansione: L'implementazione completa del metodo di Fellenius/Bishop con griglia di ricerca automatica per il fattore di sicurezza minimo verrà configurata a breve come modulo dedicato.")

with t5:
    st.subheader('Warning tecnici')
    warnings = genera_warning(d, r)
    if warnings:
        for w in warnings:
            st.warning(w)
    else:
        st.success('Nessun warning: tutte le verifiche NTC (Ribaltamento, Scorrimento, Portanza) sono soddisfatte.')

    st.subheader('Note automatiche')
    note = genera_note(d, r)
    if note:
        for n in note:
            st.info(n)

    st.subheader('Ipotesi di calcolo NTC (MAX)')
    st.markdown("""
**Metodo di calcolo adottato:**
- **Spinta attiva (Mononobe-Okabe):** Si impiega l'approccio di Coulomb / Mononobe-Okabe, che consente di considerare la componente di attrito terra-muro `δ`.
- **Combinazioni NTC 2008/2018:** La valutazione viene scissa rigorosamente fra Stato Limite EQU e Stato Limite GEO.
- **Forze d'inerzia:** Nel calcolo dei momenti destabilizzanti sismici sono incluse esplicitamente le masse del fusto, della fondazione e della zavorra.
- **Carico Limite Rigoroso:** Non si usa più un valore "ammissibile" fisso, ma si ricalcola la reale Capacità Portante per ogni combinazione tramite la formula trinomia di Brinch-Hansen, correggendo l'inclinazione dei carichi e riducendo la base efficace $B'$ a causa dell'eccentricità.
    """)
