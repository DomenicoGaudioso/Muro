# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import asdict
from typing import Tuple, List, Dict
import json
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dataclasses import dataclass

GAMMA_W = 9.81
DEFAULT_STRAT = """2.0,18,20,30,0,25000
3.0,19,21,34,0,40000
5.0,20,20,0,120,60000
"""


def parse_stratigrafia(csv_text: str) -> Tuple[pd.DataFrame, List[str]]:
    """Righe: spessore,gamma_dry,gamma_sat,phi_deg,cu_kPa,k_kN_m3"""
    err, rows = [], []
    lines = [ln.strip() for ln in csv_text.splitlines() if ln.strip()]
    if not lines:
        return pd.DataFrame(columns=['spessore_m', 'gamma_dry', 'gamma_sat', 'phi_deg', 'cu_kPa', 'k_kN_m3']), ['Inserire almeno uno strato.']
    for i, line in enumerate(lines, start=1):
        parts = [p.strip() for p in line.replace(';', ',').split(',') if p.strip()]
        if len(parts) != 6:
            err.append(f'Riga {i}: usare 6 campi = spessore,gamma_dry,gamma_sat,phi,cu,k.')
            continue
        try:
            h, gd, gs, phi, cu, k = map(float, parts)
            rows.append({'spessore_m': h, 'gamma_dry': gd, 'gamma_sat': gs, 'phi_deg': phi, 'cu_kPa': cu, 'k_kN_m3': k})
        except ValueError:
            err.append(f'Riga {i}: valori non numerici.')
    df = pd.DataFrame(rows)
    if df.empty:
        return df, err or ['Stratigrafia non valida.']
    if (df['spessore_m'] <= 0).any():
        err.append('Tutti gli spessori devono essere positivi.')
    df['z_top_m'] = df['spessore_m'].cumsum() - df['spessore_m']
    df['z_bot_m'] = df['spessore_m'].cumsum()
    return df, err


def layer_at_depth(df: pd.DataFrame, z: float) -> pd.Series:
    sel = df[(df['z_top_m'] <= z) & (df['z_bot_m'] >= z)]
    if sel.empty:
        return df.iloc[-1]
    return sel.iloc[0]


def gamma_eff(layer: pd.Series, z_mid: float, falda_depth: float) -> float:
    if z_mid <= falda_depth:
        return float(layer['gamma_dry'])
    return max(float(layer['gamma_sat']) - GAMMA_W, 1.0)


def sigma_v_eff(df: pd.DataFrame, z: float, falda_depth: float) -> float:
    s = 0.0
    for _, r in df.iterrows():
        a = max(0.0, float(r['z_top_m']))
        b = min(z, float(r['z_bot_m']))
        if b <= a:
            continue
        if falda_depth <= a:
            s += (b - a) * max(float(r['gamma_sat']) - GAMMA_W, 1.0)
        elif falda_depth >= b:
            s += (b - a) * float(r['gamma_dry'])
        else:
            s += (falda_depth - a) * float(r['gamma_dry'])
            s += (b - falda_depth) * max(float(r['gamma_sat']) - GAMMA_W, 1.0)
    return s


def u_hydro(z: float, falda_depth: float) -> float:
    return GAMMA_W * max(z - falda_depth, 0.0)


def export_json(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')


@dataclass(frozen=True)
class DatiMuro:
    H: float
    q: float
    gamma_cls: float
    B: float
    B_punta: float
    B_tallone: float
    t_base: float
    t_fusto_top: float
    t_fusto_bot: float
    mu_base: float
    q_amm: float
    h_fronte: float
    falda_retro: float
    falda_fronte: float
    kh: float
    kv: float
    include_passivo: bool = True
    stratigrafia_csv: str = DEFAULT_STRAT


def ka(phi):
    s = math.sin(math.radians(phi))
    return (1 - s) / (1 + s)


def kp(phi):
    s = math.sin(math.radians(phi))
    return (1 + s) / (1 - s)


def valida_dati(d: DatiMuro) -> List[str]:
    err = []
    if d.H <= 0: err.append('L\'altezza H deve essere positiva.')
    if d.B <= 0: err.append('La base B deve essere positiva.')
    if abs((d.B_punta + d.B_tallone) - d.B) > 1e-6: err.append('Punta + tallone deve coincidere con B.')
    if d.t_fusto_bot < d.t_fusto_top: err.append('Lo spessore del fusto al piede deve essere >= della testa.')
    if d.q_amm <= 0: err.append('q ammissibile deve essere positiva.')
    _, e2 = parse_stratigrafia(d.stratigrafia_csv)
    err.extend(e2)
    return err


def integrate_pressures(df, H, falda, q_sur, kh=0.0):
    z = np.linspace(0, H, 300)
    sig = []
    for zi in z:
        lay = layer_at_depth(df, zi)
        phi = float(lay['phi_deg'])
        Ka = ka(phi) if phi > 0 else 1.0
        sv = sigma_v_eff(df, zi, falda)
        u = u_hydro(zi, falda)
        sig_h = Ka * sv + u + Ka * q_sur + kh * sv
        sig.append(sig_h)
    sig = np.array(sig)
    P = np.trapz(sig, z)
    zbar = np.trapz(sig * z, z) / max(P, 1e-9)
    return z, sig, P, zbar


def integrate_passive(df, h_front, falda_front, kh=0.0):
    if h_front <= 0:
        return np.array([0.0]), np.array([0.0]), 0.0, 0.0
    z = np.linspace(0, h_front, 200)
    sig = []
    for zi in z:
        lay = layer_at_depth(df, zi)
        phi = float(lay['phi_deg'])
        Kp = kp(phi) if phi > 0 else 1.0
        sv = sigma_v_eff(df, zi, falda_front)
        u = u_hydro(zi, falda_front)
        sig_h = max((Kp - kh) * sv + u, 0.0)
        sig.append(sig_h)
    sig = np.array(sig)
    P = np.trapz(sig, z)
    zbar = np.trapz(sig * z, z) / max(P, 1e-9)
    return z, sig, P, zbar


def evaluate_case(d: DatiMuro, seismic=False) -> Dict[str, float]:
    df, _ = parse_stratigrafia(d.stratigrafia_csv)
    kh = d.kh if seismic else 0.0
    kv = d.kv if seismic else 0.0
    z, sig_a, Pa, z_pa = integrate_pressures(df, d.H, d.falda_retro, d.q, kh)
    zf, sig_p, Pp, z_pp = integrate_passive(df, min(d.h_fronte, d.H), d.falda_fronte, kh if d.include_passivo else 0.0)
    if not d.include_passivo:
        Pp, z_pp = 0.0, 0.0

    # pesi strutturali e del terreno a tallone
    A_base = d.B * d.t_base
    W_base = A_base * d.gamma_cls
    x_base = d.B / 2.0
    A_fusto = 0.5 * (d.t_fusto_top + d.t_fusto_bot) * d.H
    W_fusto = A_fusto * d.gamma_cls
    x_fusto = d.B_punta - d.t_fusto_bot / 2.0
    # gamma efficace medio calcolato come sigma_v / H
    gam_eff = sigma_v_eff(df, d.H, d.falda_retro) / max(d.H, 1e-9)
    W_heel = d.B_tallone * d.H * gam_eff
    x_heel = d.B_punta + d.B_tallone / 2.0
    Wq = d.q * d.B_tallone
    x_q = x_heel
    V = (W_base + W_fusto + W_heel + Wq) * (1.0 - kv)
    Mr = W_base * x_base + W_fusto * x_fusto + W_heel * x_heel + Wq * x_q + Pp * z_pp
    Mo = Pa * z_pa
    FS_rib = Mr / max(Mo, 1e-9)
    cu_base = float(df.iloc[-1]['cu_kPa'])
    Rf = d.mu_base * V + cu_base * d.B + Pp
    FS_scorr = Rf / max(Pa, 1e-9)
    M_net = Mr - Mo
    x_R = M_net / max(V, 1e-9)
    e = d.B / 2.0 - x_R
    q_med = V / d.B
    qmax = q_med * (1 + 6 * e / d.B)
    qmin = q_med * (1 - 6 * e / d.B)
    return {
        'Pa': Pa, 'Pp': Pp,
        'FS_rib': FS_rib, 'FS_scorr': FS_scorr,
        'qmax': qmax, 'qmin': qmin,
        'z_a': z, 'sig_a': sig_a,
        'z_p': zf, 'sig_p': sig_p,
    }


def calcola_muro(d: DatiMuro) -> Dict[str, object]:
    df, _ = parse_stratigrafia(d.stratigrafia_csv)
    st = evaluate_case(d, seismic=False)
    se = evaluate_case(d, seismic=True)
    return {'stratigrafia': df, 'statico': st, 'sismico': se}


def tabella_sintesi(d: DatiMuro, r: Dict[str, object]) -> pd.DataFrame:
    st, se = r['statico'], r['sismico']
    rows = [
        ('Pa [kN/m]', st['Pa'], se['Pa']),
        ('Pp [kN/m]', st['Pp'], se['Pp']),
        ('FS ribaltamento [-]', st['FS_rib'], se['FS_rib']),
        ('FS scorrimento [-]', st['FS_scorr'], se['FS_scorr']),
        ('qmax [kPa]', st['qmax'], se['qmax']),
        ('qmin [kPa]', st['qmin'], se['qmin']),
    ]
    return pd.DataFrame(rows, columns=['Parametro', 'Statico', 'Sismico'])


# ---------------------------------------------------------------------------
# Warning e note tecniche automatiche
# ---------------------------------------------------------------------------

def genera_warning(d: DatiMuro, r: dict) -> List[str]:
    """Ritorna una lista di stringhe di warning quando le verifiche sono critiche."""
    warnings = []
    st = r['statico']
    se = r['sismico']
    fs_rib_stat = st['FS_rib']
    fs_rib_sism = se['FS_rib']
    fs_scorr_stat = st['FS_scorr']
    fs_scorr_sism = se['FS_scorr']
    qmax = st['qmax']
    qmin = st['qmin']

    if fs_rib_stat < 1.5:
        warnings.append(f"⚠ FS ribaltamento statico basso ({fs_rib_stat:.2f} < 1.5)")
    if fs_scorr_stat < 1.5:
        warnings.append(f"⚠ FS scorrimento statico basso ({fs_scorr_stat:.2f} < 1.5)")
    if fs_rib_sism < 1.1:
        warnings.append(f"⚠ FS ribaltamento sismico molto basso ({fs_rib_sism:.2f} < 1.1)")
    if fs_scorr_sism < 1.1:
        warnings.append(f"⚠ FS scorrimento sismico molto basso ({fs_scorr_sism:.2f} < 1.1)")
    if qmax > d.q_amm:
        warnings.append(f"⚠ Pressione massima ({qmax:.1f} kPa) supera q_amm ({d.q_amm:.1f} kPa)")
    if qmin < 0:
        warnings.append(f"⚠ Pressione minima negativa ({qmin:.1f} kPa): possibile sollevamento della fondazione")
    if d.falda_retro < d.H:
        warnings.append("ℹ Falda a tergo attiva: influenza significativa sulle spinte")
    # riduzione relativa del FS per effetto sismico > 30%
    if abs(fs_rib_stat - fs_rib_sism) / max(fs_rib_stat, 1e-9) > 0.3:
        warnings.append("⚠ Il caso sismico riduce significativamente il FS ribaltamento")
    if abs(fs_scorr_stat - fs_scorr_sism) / max(fs_scorr_stat, 1e-9) > 0.3:
        warnings.append("⚠ Il caso sismico riduce significativamente il FS scorrimento")
    return warnings


def genera_note(d: DatiMuro, r: dict) -> List[str]:
    """Ritorna note tecniche interpretative automatiche sui risultati."""
    note = []
    st = r['statico']
    se = r['sismico']
    fs_rib_stat = st['FS_rib']
    fs_rib_sism = se['FS_rib']
    fs_scorr_stat = st['FS_scorr']
    fs_scorr_sism = se['FS_scorr']
    qmax = st['qmax']

    # meccanismo governante (caso statico)
    if fs_scorr_stat < fs_rib_stat:
        note.append("Il meccanismo di scorrimento governa sul ribaltamento")
    elif fs_rib_stat < fs_scorr_stat:
        note.append("Il meccanismo di ribaltamento governa sullo scorrimento")

    # il caso sismico governa entrambe le verifiche
    if fs_rib_sism < fs_rib_stat and fs_scorr_sism < fs_scorr_stat:
        note.append("Il caso sismico governa in tutte le verifiche")

    if d.include_passivo:
        note.append("Il contributo passivo a fronte è incluso nel calcolo dello scorrimento")

    # falda nella metà superiore del terrapieno
    if d.falda_retro < d.H / 2:
        note.append("La falda è nella metà superiore del terrapieno: le pressioni idrostatiche sono preponderanti")

    # utilizzo capacità portante
    utilizzo = qmax / max(d.q_amm, 1e-9)
    if utilizzo < 0.7:
        note.append("Le pressioni di contatto sono ampiamente entro i limiti (utilizzo < 70%)")
    elif utilizzo > 0.9:
        note.append("Le pressioni di contatto sono prossime al limite ammissibile (utilizzo > 90%)")

    return note


# ---------------------------------------------------------------------------
# Figura geometria (migliorata)
# ---------------------------------------------------------------------------

def figura_geometria(d: DatiMuro) -> go.Figure:
    """
    Disegna la geometria del muro con:
    - Muro in grigio chiaro
    - Terreno a tergo color sienna/tan
    - Banda falda semitrasparente blu (se falda a tergo attiva)
    - Terreno a fronte color peru
    - Annotazioni per le quote principali
    """
    fig = go.Figure()

    # quota sommità muro
    H_tot = d.t_base + d.H

    # ---- Muro (calcestruzzo) ------------------------------------------------
    xf = d.B_punta                   # x spigolo interno fusto
    xft = xf - d.t_fusto_bot         # x spigolo esterno fusto al piede
    x_muro = [0, d.B, d.B, xft, xf - d.t_fusto_top, xf, xf, 0, 0]
    y_muro = [0, 0, d.t_base, d.t_base, H_tot, H_tot, d.t_base, d.t_base, 0]
    fig.add_trace(go.Scatter(
        x=x_muro, y=y_muro,
        fill='toself', fillcolor='lightgray',
        name='Muro (cls)',
        mode='lines',
        line=dict(color='black', width=1.5),
    ))

    # ---- Terreno a tergo ----------------------------------------------------
    fig.add_trace(go.Scatter(
        x=[xf, d.B, d.B, xf],
        y=[d.t_base, d.t_base, H_tot, H_tot],
        fill='toself', fillcolor='tan',
        name='Terreno a tergo',
        mode='lines',
        line=dict(color='sienna', width=1),
    ))

    # ---- Terreno a fronte ---------------------------------------------------
    if d.h_fronte > 0:
        hf = min(d.h_fronte, d.H)
        fig.add_trace(go.Scatter(
            x=[0, xf, xf, 0],
            y=[d.t_base, d.t_base, d.t_base + hf, d.t_base + hf],
            fill='toself', fillcolor='peru',
            name='Terreno a fronte',
            mode='lines',
            line=dict(color='saddlebrown', width=1),
        ))

    # ---- Banda falda a tergo (semitrasparente) --------------------------------
    if d.falda_retro < d.H:
        y_falda = d.t_base + d.falda_retro
        fig.add_trace(go.Scatter(
            x=[xf, d.B, d.B, xf],
            y=[y_falda, y_falda, H_tot, H_tot],
            fill='toself',
            fillcolor='rgba(0, 100, 220, 0.20)',
            name='Zona satura (tergo)',
            mode='lines',
            line=dict(color='blue', width=1, dash='dot'),
        ))

    # ---- Falda a fronte (linea tratteggiata) ---------------------------------
    if d.falda_fronte < d.h_fronte:
        fig.add_hline(
            y=d.t_base + d.falda_fronte,
            line_dash='dot', line_color='cyan',
            annotation_text='Falda fronte',
        )

    # ---- Annotazioni quote principali ----------------------------------------
    # H totale (freccia verticale sul lato sinistro)
    fig.add_annotation(
        x=-0.3, y=H_tot / 2,
        text=f"H tot = {H_tot:.2f} m",
        showarrow=False,
        xanchor='right',
        font=dict(size=11, color='black'),
    )
    # spessore base
    fig.add_annotation(
        x=d.B / 2, y=d.t_base / 2,
        text=f"t_base = {d.t_base:.2f} m",
        showarrow=False,
        font=dict(size=10, color='dimgray'),
    )
    # altezza terreno a fronte
    if d.h_fronte > 0:
        fig.add_annotation(
            x=-0.05, y=d.t_base + d.h_fronte / 2,
            text=f"h_fr = {d.h_fronte:.2f} m",
            showarrow=False,
            xanchor='right',
            font=dict(size=10, color='saddlebrown'),
        )

    fig.update_layout(
        title='Geometria del muro',
        xaxis_title='x [m]',
        yaxis_title='y [m]',
        template='plotly_white',
        legend=dict(orientation='h', y=-0.15),
    )
    fig.update_yaxes(scaleanchor='x', scaleratio=1)
    return fig


# ---------------------------------------------------------------------------
# Figura output pressioni (migliorata con subplots)
# ---------------------------------------------------------------------------

def figura_output(r: Dict[str, object]) -> go.Figure:
    """
    Subplot a 2 pannelli:
    - Pannello sinistro: pressioni attive a tergo (statico e sismico)
    - Pannello destro: pressioni passive a fronte (statico e sismico), se Pp > 0
    Le pressioni passive hanno y riferita al fronte (da 0 a h_fronte).
    """
    st = r['statico']
    se = r['sismico']

    ha_passivo = st['Pp'] > 0 or se['Pp'] > 0

    if ha_passivo:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Pressioni attive a tergo', 'Pressioni passive a fronte'),
            shared_yaxes=False,
        )
    else:
        fig = make_subplots(rows=1, cols=1, subplot_titles=('Pressioni attive a tergo',))

    # ---- Pannello sinistro: pressioni attive ---------------------------------
    fig.add_trace(
        go.Scatter(
            x=st['sig_a'], y=st['z_a'],
            mode='lines', fill='tozerox',
            name='Attiva statica',
            line=dict(color='royalblue'),
            fillcolor='rgba(65, 105, 225, 0.20)',
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=se['sig_a'], y=se['z_a'],
            mode='lines',
            name='Attiva sismica',
            line=dict(color='firebrick', dash='dash'),
        ),
        row=1, col=1,
    )

    # ---- Pannello destro: pressioni passive (se presenti) --------------------
    if ha_passivo:
        fig.add_trace(
            go.Scatter(
                x=st['sig_p'], y=st['z_p'],
                mode='lines', fill='tozerox',
                name='Passiva statica',
                line=dict(color='seagreen'),
                fillcolor='rgba(46, 139, 87, 0.20)',
            ),
            row=1, col=2,
        )
        fig.add_trace(
            go.Scatter(
                x=se['sig_p'], y=se['z_p'],
                mode='lines',
                name='Passiva sismica',
                line=dict(color='darkorange', dash='dash'),
            ),
            row=1, col=2,
        )
        fig.update_xaxes(title_text='σh [kPa]', row=1, col=2)
        fig.update_yaxes(title_text='z fronte [m]', autorange='reversed', row=1, col=2)

    fig.update_xaxes(title_text='σh [kPa]', row=1, col=1)
    fig.update_yaxes(title_text='z [m]', autorange='reversed', row=1, col=1)
    fig.update_layout(
        title='Diagrammi delle pressioni laterali',
        template='plotly_white',
        legend=dict(orientation='h', y=-0.18),
    )
    return fig
