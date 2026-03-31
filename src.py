# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Tuple, List, Dict
import json
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    delta_muro: float = 20.0  # Attrito terra-muro (NOVITA' MAX)
    include_passivo: bool = True
    stratigrafia_csv: str = DEFAULT_STRAT

def ka_mo(phi_deg, delta_deg, kh, kv):
    """Calcolo K_A con Mononobe-Okabe (Metodo MAX)"""
    phi = math.radians(phi_deg)
    delta = math.radians(delta_deg)
    theta = math.atan(kh / (1 - kv)) if (1-kv) != 0 else 0.0
    
    if phi - theta <= 0:
        theta = max(0.0, phi - 0.001)
        
    num = (math.cos(phi - theta))**2
    den_part1 = math.cos(theta) * math.cos(delta + theta)
    den_part2 = (1 + math.sqrt(math.sin(phi + delta) * math.sin(phi - theta) / math.cos(delta + theta)))**2
    return (num / (den_part1 * den_part2)) * (1 - kv)

def kp(phi):
    """Spinta passiva (Rankine)"""
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

def integrate_pressures_ntc(df, H, falda, q_sur, delta_muro, kh=0.0, kv=0.0, gamma_phi=1.0, gamma_Q=1.0, gamma_G=1.0):
    z = np.linspace(0, H, 300)
    sig_h, sig_v = [], []
    for zi in z:
        lay = layer_at_depth(df, zi)
        phi_d = math.degrees(math.atan(math.tan(math.radians(float(lay['phi_deg']))) / gamma_phi))
        Ka = ka_mo(phi_d, delta_muro, kh, kv) if phi_d > 0 else 1.0
        
        sv = sigma_v_eff(df, zi, falda) * gamma_G
        u = u_hydro(zi, falda) * gamma_G
        
        # Spinta totale orizzontale e verticale
        p_tot = Ka * sv + Ka * (q_sur * gamma_Q)
        sig_h.append(p_tot * math.cos(math.radians(delta_muro)) + u)
        sig_v.append(p_tot * math.sin(math.radians(delta_muro)))
        
    sig_h = np.array(sig_h)
    sig_v = np.array(sig_v)
    Ph = np.trapz(sig_h, z)
    Pv = np.trapz(sig_v, z)
    zbar_h = np.trapz(sig_h * z, z) / max(Ph, 1e-9) if Ph > 0 else 0.0
    return z, sig_h, Ph, Pv, zbar_h

def integrate_passive(df, h_front, falda_front, gamma_phi=1.0, gamma_G=1.0, kh=0.0):
    if h_front <= 0:
        return np.array([0.0]), np.array([0.0]), 0.0, 0.0
    z = np.linspace(0, h_front, 200)
    sig = []
    for zi in z:
        lay = layer_at_depth(df, zi)
        phi_d = math.degrees(math.atan(math.tan(math.radians(float(lay['phi_deg']))) / gamma_phi))
        Kp = kp(phi_d) if phi_d > 0 else 1.0
        sv = sigma_v_eff(df, zi, falda_front) * gamma_G
        u = u_hydro(zi, falda_front) * gamma_G
        sig_h = max((Kp - kh) * sv + u, 0.0)
        sig.append(sig_h)
    sig = np.array(sig)
    P = np.trapz(sig, z)
    zbar = np.trapz(sig * z, z) / max(P, 1e-9)
    return z, sig, P, zbar

def evaluate_ntc_combination(d: DatiMuro, df: pd.DataFrame, tipo: str, kh: float, kv: float, g_phi: float, g_stab: float, g_dest: float, g_q: float) -> Dict[str, float]:
    # Spinte Attive (NTC)
    z, sig_h, Ph, Pv, zbar_h = integrate_pressures_ntc(df, d.H, d.falda_retro, d.q, d.delta_muro, kh, kv, g_phi, g_q, g_dest)
    
    # Spinte Passive
    zf, sig_p, Pp, z_pp = integrate_passive(df, min(d.h_fronte, d.H), d.falda_fronte, g_phi, g_stab, kh if d.include_passivo else 0.0)
    if not d.include_passivo: Pp, z_pp = 0.0, 0.0

    # Pesi e Masse Strutturali
    A_base = d.B * d.t_base
    W_base = A_base * d.gamma_cls * g_stab
    x_base = d.B / 2.0
    
    A_fusto = 0.5 * (d.t_fusto_top + d.t_fusto_bot) * d.H
    W_fusto = A_fusto * d.gamma_cls * g_stab
    x_fusto = d.B_punta + (d.t_fusto_bot / 2.0)
    
    gam_eff = sigma_v_eff(df, d.H, d.falda_retro) / max(d.H, 1e-9)
    W_heel = d.B_tallone * d.H * gam_eff * g_stab
    x_heel = d.B_punta + d.t_fusto_bot + (d.B_tallone / 2.0)
    
    Wq = d.q * d.B_tallone * g_q
    x_q = x_heel

    # Forze d'inerzia (Metodo MAX)
    F_base = kh * (W_base / g_stab)
    F_fusto = kh * (W_fusto / g_stab)
    F_heel = kh * (W_heel / g_stab)

    # Risultanti e Momenti rispetto alla punta (x=0, y=0)
    V_tot = (W_base + W_fusto + W_heel + Wq) * (1.0 - kv) + Pv
    H_tot = Ph + F_base + F_fusto + F_heel
    
    M_stab = W_base * x_base + W_fusto * x_fusto + W_heel * x_heel + Wq * x_q + Pp * z_pp + Pv * d.B
    M_destab = Ph * zbar_h + F_base * (d.t_base/2) + F_fusto * (d.t_base + d.H/2) + F_heel * (d.t_base + d.H/2)
    
    FS_rib = M_stab / max(M_destab, 1e-9)

    # Scorrimento
    cu_base = float(df.iloc[-1]['cu_kPa']) / g_phi
    Rf = d.mu_base * V_tot + cu_base * d.B + Pp
    FS_scorr = Rf / max(H_tot, 1e-9)

    # Schiacciamento / Pressioni
    M_net = M_destab - M_stab + (V_tot * d.B / 2.0)
    e = M_net / max(V_tot, 1e-9)
    q_med = V_tot / d.B
    qmax = q_med * (1 + 6 * abs(e) / d.B)
    qmin = q_med * (1 - 6 * abs(e) / d.B)
    if qmin < 0:
        u = d.B / 2.0 - abs(e)
        qmax = (2.0 * V_tot) / (3.0 * u) if u > 0 else 0
        qmin = 0.0

    return {
        'Tipo': tipo, 'Pa': Ph, 'Pp': Pp,
        'FS_rib': FS_rib, 'FS_scorr': FS_scorr,
        'qmax': qmax, 'qmin': qmin,
        'z_a': z, 'sig_a': sig_h,
        'z_p': zf, 'sig_p': sig_p,
    }

def calcola_muro(d: DatiMuro) -> Dict[str, object]:
    df, _ = parse_stratigrafia(d.stratigrafia_csv)
    
    # 1. Statica EQU (Ribaltamento)
    st_EQU = evaluate_ntc_combination(d, df, "Statica_EQU", 0.0, 0.0, 1.25, 0.9, 1.1, 1.5)
    # 2. Statica GEO (Scorrimento, Portanza)
    st_GEO = evaluate_ntc_combination(d, df, "Statica_GEO", 0.0, 0.0, 1.25, 1.0, 1.0, 1.3)
    # 3. Sismica GEO kv+
    se_pos = evaluate_ntc_combination(d, df, "Sismica_kv_pos", d.kh, d.kv, 1.25, 1.0, 1.0, 1.0)
    # 4. Sismica GEO kv-
    se_neg = evaluate_ntc_combination(d, df, "Sismica_kv_neg", d.kh, -d.kv, 1.25, 1.0, 1.0, 1.0)
    
    return {'stratigrafia': df, 'statico': st_GEO, 'sismico': se_pos, 'st_EQU': st_EQU, 'se_neg': se_neg}

def tabella_sintesi(d: DatiMuro, r: Dict[str, object]) -> pd.DataFrame:
    st = r['statico']
    se = r['sismico']
    rows = [
        ('Pa (Spinta Orizz.) [kN/m]', st['Pa'], se['Pa']),
        ('Pp (Spinta Passiva) [kN/m]', st['Pp'], se['Pp']),
        ('FS ribaltamento [-]', r['st_EQU']['FS_rib'], se['FS_rib']),
        ('FS scorrimento [-]', st['FS_scorr'], se['FS_scorr']),
        ('qmax [kPa]', st['qmax'], se['qmax']),
        ('qmin [kPa]', st['qmin'], se['qmin']),
    ]
    return pd.DataFrame(rows, columns=['Parametro', 'Statico (GEO/EQU)', 'Sismico kv+'])

# ---------------------------------------------------------------------------
# Warning e note tecniche automatiche (Mantenute le tue originali!)
# ---------------------------------------------------------------------------

def genera_warning(d: DatiMuro, r: dict) -> List[str]:
    warnings = []
    st_EQU = r['st_EQU']
    st_GEO = r['statico']
    se = r['sismico']
    
    if st_EQU['FS_rib'] < 1.0:
        warnings.append(f"⚠ FS ribaltamento statico (EQU) non soddisfatto ({st_EQU['FS_rib']:.2f} < 1.0)")
    if st_GEO['FS_scorr'] < 1.0:
        warnings.append(f"⚠ FS scorrimento statico (GEO) non soddisfatto ({st_GEO['FS_scorr']:.2f} < 1.0)")
    if se['FS_rib'] < 1.0:
        warnings.append(f"⚠ FS ribaltamento sismico non soddisfatto ({se['FS_rib']:.2f} < 1.0)")
    if se['FS_scorr'] < 1.0:
        warnings.append(f"⚠ FS scorrimento sismico non soddisfatto ({se['FS_scorr']:.2f} < 1.0)")
    
    qmax_max = max(st_GEO['qmax'], se['qmax'])
    if qmax_max > d.q_amm:
        warnings.append(f"⚠ Pressione massima ({qmax_max:.1f} kPa) supera q_amm ({d.q_amm:.1f} kPa)")
    if st_GEO['qmin'] == 0 or se['qmin'] == 0:
        warnings.append(f"⚠ Pressione minima nulla: parzializzazione della sezione di fondazione rilevata.")
    if d.falda_retro < d.H:
        warnings.append("ℹ Falda a tergo attiva: influenza significativa sulle spinte")
    return warnings

def genera_note(d: DatiMuro, r: dict) -> List[str]:
    note = []
    if d.include_passivo:
        note.append("Il contributo passivo a fronte è incluso nel calcolo dello scorrimento e ribaltamento.")
    if d.falda_retro < d.H / 2:
        note.append("La falda è nella metà superiore del terrapieno: le pressioni idrostatiche sono preponderanti.")
    utilizzo = r['statico']['qmax'] / max(d.q_amm, 1e-9)
    if utilizzo < 0.7:
        note.append("Le pressioni di contatto sono ampiamente entro i limiti (utilizzo < 70%).")
    elif utilizzo > 0.9:
        note.append("Le pressioni di contatto sono prossime al limite ammissibile (utilizzo > 90%).")
    note.append("Metodo MAX: Il calcolo differenzia le combinazioni EQU e GEO applicando coefficienti parziali e forze d'inerzia.")
    return note

# ---------------------------------------------------------------------------
# Visualizzazioni originali (Mantenute le tue Plotly!)
# ---------------------------------------------------------------------------

def figura_geometria(d: DatiMuro) -> go.Figure:
    fig = go.Figure()
    H_tot = d.t_base + d.H
    xf = d.B_punta
    xft = xf + d.t_fusto_bot
    x_muro = [0, d.B, d.B, xft, xf + d.t_fusto_top, xf, xf, 0, 0]
    y_muro = [0, 0, d.t_base, d.t_base, H_tot, H_tot, d.t_base, d.t_base, 0]
    
    fig.add_trace(go.Scatter(x=x_muro, y=y_muro, fill='toself', fillcolor='lightgray', name='Muro (cls)', line=dict(color='black', width=1.5)))
    fig.add_trace(go.Scatter(x=[xft, d.B, d.B+2, xft], y=[d.t_base, d.t_base, H_tot, H_tot], fill='toself', fillcolor='tan', name='Terreno a tergo', line=dict(color='sienna', width=1)))
    
    if d.h_fronte > 0:
        hf = min(d.h_fronte, d.H)
        fig.add_trace(go.Scatter(x=[0, xf, xf, 0], y=[d.t_base, d.t_base, d.t_base + hf, d.t_base + hf], fill='toself', fillcolor='peru', name='Terreno a fronte', line=dict(color='saddlebrown', width=1)))

    if d.falda_retro < d.H:
        y_falda = d.t_base + d.falda_retro
        fig.add_trace(go.Scatter(x=[xft, d.B, d.B+2, xft], y=[y_falda, y_falda, H_tot, H_tot], fill='toself', fillcolor='rgba(0, 100, 220, 0.20)', name='Zona satura (tergo)', line=dict(color='blue', width=1, dash='dot')))

    fig.add_annotation(x=-0.3, y=H_tot / 2, text=f"H tot = {H_tot:.2f} m", showarrow=False, xanchor='right', font=dict(size=11, color='black'))
    
    fig.update_layout(title='Geometria del muro', xaxis_title='x [m]', yaxis_title='y [m]', template='plotly_white', legend=dict(orientation='h', y=-0.15))
    fig.update_yaxes(scaleanchor='x', scaleratio=1)
    return fig

def figura_output(r: Dict[str, object]) -> go.Figure:
    st = r['statico']
    se = r['sismico']
    ha_passivo = st['Pp'] > 0 or se['Pp'] > 0

    if ha_passivo:
        fig = make_subplots(rows=1, cols=2, subplot_titles=('Pressioni attive a tergo', 'Pressioni passive a fronte'), shared_yaxes=False)
    else:
        fig = make_subplots(rows=1, cols=1, subplot_titles=('Pressioni attive a tergo',))

    fig.add_trace(go.Scatter(x=st['sig_a'], y=st['z_a'], mode='lines', fill='tozerox', name='Attiva statica (GEO)', line=dict(color='royalblue'), fillcolor='rgba(65, 105, 225, 0.20)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=se['sig_a'], y=se['z_a'], mode='lines', name='Attiva sismica', line=dict(color='firebrick', dash='dash')), row=1, col=1)

    if ha_passivo:
        fig.add_trace(go.Scatter(x=st['sig_p'], y=st['z_p'], mode='lines', fill='tozerox', name='Passiva statica', line=dict(color='seagreen'), fillcolor='rgba(46, 139, 87, 0.20)'), row=1, col=2)
        fig.add_trace(go.Scatter(x=se['sig_p'], y=se['z_p'], mode='lines', name='Passiva sismica', line=dict(color='darkorange', dash='dash')), row=1, col=2)
        fig.update_xaxes(title_text='σh [kPa]', row=1, col=2)
        fig.update_yaxes(title_text='z fronte [m]', autorange='reversed', row=1, col=2)

    fig.update_xaxes(title_text='σh [kPa]', row=1, col=1)
    fig.update_yaxes(title_text='z [m]', autorange='reversed', row=1, col=1)
    fig.update_layout(title='Diagrammi delle pressioni laterali', template='plotly_white', legend=dict(orientation='h', y=-0.18))
    return fig
