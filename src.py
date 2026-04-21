# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
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


def integra_trapezi(y, x) -> float:
    return float(np.trapz(y, x))


def parse_stratigrafia(csv_text: str) -> Tuple[pd.DataFrame, List[str]]:
    err, rows = [], []
    lines = [ln.strip() for ln in csv_text.splitlines() if ln.strip()]
    if not lines:
        columns = ["spessore_m", "gamma_dry", "gamma_sat", "phi_deg", "cu_kPa", "k_kN_m3"]
        return pd.DataFrame(columns=columns), ["Inserire almeno uno strato."]

    for i, line in enumerate(lines, start=1):
        parts = [p.strip() for p in line.replace(";", ",").split(",") if p.strip()]
        if len(parts) != 6:
            err.append(f"Riga {i}: usare 6 campi = spessore,gamma_dry,gamma_sat,phi,cu,k.")
            continue
        try:
            h, gd, gs, phi, cu, k = map(float, parts)
            rows.append(
                {
                    "spessore_m": h,
                    "gamma_dry": gd,
                    "gamma_sat": gs,
                    "phi_deg": phi,
                    "cu_kPa": cu,
                    "k_kN_m3": k,
                }
            )
        except ValueError:
            err.append(f"Riga {i}: valori non numerici.")

    df = pd.DataFrame(rows)
    if df.empty:
        return df, err or ["Stratigrafia non valida."]
    if (df["spessore_m"] <= 0).any():
        err.append("Tutti gli spessori devono essere positivi.")
    df["z_top_m"] = df["spessore_m"].cumsum() - df["spessore_m"]
    df["z_bot_m"] = df["spessore_m"].cumsum()
    return df, err


def layer_at_depth(df: pd.DataFrame, z: float) -> pd.Series:
    sel = df[(df["z_top_m"] <= z) & (df["z_bot_m"] >= z)]
    if sel.empty:
        return df.iloc[-1]
    return sel.iloc[0]


def sigma_v_eff(df: pd.DataFrame, z: float, falda_depth: float) -> float:
    sigma = 0.0
    for _, row in df.iterrows():
        a = max(0.0, float(row["z_top_m"]))
        b = min(z, float(row["z_bot_m"]))
        if b <= a:
            continue
        if falda_depth <= a:
            sigma += (b - a) * max(float(row["gamma_sat"]) - GAMMA_W, 1.0)
        elif falda_depth >= b:
            sigma += (b - a) * float(row["gamma_dry"])
        else:
            sigma += (falda_depth - a) * float(row["gamma_dry"])
            sigma += (b - falda_depth) * max(float(row["gamma_sat"]) - GAMMA_W, 1.0)
    return sigma


def u_hydro(z: float, falda_depth: float) -> float:
    return GAMMA_W * max(z - falda_depth, 0.0)


def export_json(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


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
    delta_muro: float = 20.0
    include_passivo: bool = True
    stratigrafia_csv: str = DEFAULT_STRAT
    ha_tirante: bool = False
    t_quota: float = 0.0
    t_inclinazione: float = 15.0
    t_tiro: float = 0.0
    analizza_pendio: bool = False
    pendio_H: float = 5.0
    pendio_beta: float = 26.0
    pendio_berma: float = 6.0


def valida_dati(d: DatiMuro) -> List[str]:
    err = []
    if d.H <= 0:
        err.append("L'altezza H deve essere positiva.")
    if d.B <= 0:
        err.append("La base B deve essere positiva.")
    if abs((d.B_punta + d.B_tallone) - d.B) > 1e-6:
        err.append("Punta + tallone deve coincidere con B.")
    if d.t_fusto_bot < d.t_fusto_top:
        err.append("Lo spessore del fusto al piede deve essere >= della testa.")
    if d.q_amm <= 0:
        err.append("q ammissibile deve essere positiva.")
    if d.h_fronte < 0:
        err.append("L'altezza del terreno a fronte non puo essere negativa.")
    if d.h_fronte > d.H:
        err.append("L'altezza del terreno a fronte non puo superare H.")
    if d.ha_tirante and d.t_tiro <= 0:
        err.append("Con tirante attivo il tiro deve essere positivo.")
    if d.ha_tirante and d.t_quota > (d.H + d.t_base):
        err.append("La quota del tirante deve ricadere entro l'altezza del modello.")
    if d.analizza_pendio and d.pendio_H <= 0:
        err.append("L'altezza del pendio deve essere positiva.")
    if d.analizza_pendio and not (10 <= d.pendio_beta < 80):
        err.append("L'inclinazione del pendio deve essere compresa tra 10 e 80 gradi.")
    if d.analizza_pendio and d.pendio_berma <= 0:
        err.append("La berma di monte del pendio deve essere positiva.")

    _, strat_errors = parse_stratigrafia(d.stratigrafia_csv)
    err.extend(strat_errors)
    return err


def ka_mo(phi_deg, delta_deg, kh, kv):
    phi = math.radians(phi_deg)
    delta = math.radians(delta_deg)
    theta = math.atan(kh / (1 - kv)) if (1 - kv) != 0 else 0.0
    if phi - theta <= 0:
        theta = max(0.0, phi - 0.001)
    num = math.cos(phi - theta) ** 2
    den_part1 = math.cos(theta) * math.cos(delta + theta)
    den_part2 = (1 + math.sqrt(math.sin(phi + delta) * math.sin(phi - theta) / math.cos(delta + theta))) ** 2
    return (num / (den_part1 * den_part2)) * (1 - kv)


def kp(phi):
    s = math.sin(math.radians(phi))
    return (1 + s) / (1 - s)


def integrate_pressures_ntc(df, H, falda, q_sur, delta_muro, kh=0.0, kv=0.0, gamma_phi=1.0, gamma_Q=1.0, gamma_G=1.0):
    z = np.linspace(0, H, 300)
    sig_h, sig_v = [], []
    for zi in z:
        lay = layer_at_depth(df, zi)
        phi_d = math.degrees(math.atan(math.tan(math.radians(float(lay["phi_deg"]))) / gamma_phi))
        Ka = ka_mo(phi_d, delta_muro, kh, kv) if phi_d > 0 else 1.0
        sv = sigma_v_eff(df, zi, falda) * gamma_G
        u = u_hydro(zi, falda) * gamma_G
        p_tot = Ka * sv + Ka * (q_sur * gamma_Q)
        sig_h.append(p_tot * math.cos(math.radians(delta_muro)) + u)
        sig_v.append(p_tot * math.sin(math.radians(delta_muro)))

    sig_h = np.array(sig_h)
    sig_v = np.array(sig_v)
    Ph = integra_trapezi(sig_h, z)
    Pv = integra_trapezi(sig_v, z)
    zbar_h = integra_trapezi(sig_h * z, z) / max(Ph, 1e-9) if Ph > 0 else 0.0
    return z, sig_h, Ph, Pv, zbar_h


def integrate_passive(df, h_front, falda_front, gamma_phi=1.0, gamma_G=1.0, kh=0.0):
    if h_front <= 0:
        return np.array([0.0]), np.array([0.0]), 0.0, 0.0
    z = np.linspace(0, h_front, 200)
    sig = []
    for zi in z:
        lay = layer_at_depth(df, zi)
        phi_d = math.degrees(math.atan(math.tan(math.radians(float(lay["phi_deg"]))) / gamma_phi))
        Kp = kp(phi_d) if phi_d > 0 else 1.0
        sv = sigma_v_eff(df, zi, falda_front) * gamma_G
        u = u_hydro(zi, falda_front) * gamma_G
        sig.append(max((Kp - kh) * sv + u, 0.0))
    sig = np.array(sig)
    P = integra_trapezi(sig, z)
    zbar_p = integra_trapezi(sig * z, z) / max(P, 1e-9) if P > 0 else 0.0
    return z, sig, P, zbar_p


def fattori_capacita_portante(phi_deg):
    if phi_deg <= 0:
        return 5.14, 1.0, 0.0
    phi = math.radians(phi_deg)
    Nq = math.exp(math.pi * math.tan(phi)) * (math.tan(math.radians(45 + phi_deg / 2))) ** 2
    Nc = (Nq - 1) / math.tan(phi)
    Ngamma = 2 * (Nq + 1) * math.tan(phi)
    return Nc, Nq, Ngamma


def calcola_qlim_hansen(B_eff, V_tot, H_tot, gamma_fond, phi_fond, c_fond, q_sovraccarico):
    Nc, Nq, Ngamma = fattori_capacita_portante(phi_fond)
    V_calc = max(V_tot, 1e-9)
    if phi_fond > 0:
        tan_term = 1 / math.tan(math.radians(max(phi_fond, 1)))
        iq = (1 - 0.5 * H_tot / (V_calc + B_eff * c_fond * tan_term)) ** 5
        igamma = (1 - 0.7 * H_tot / (V_calc + B_eff * c_fond * tan_term)) ** 5
        ic = iq - (1 - iq) / (Nc * math.tan(math.radians(max(phi_fond, 1))))
    else:
        iq = 1.0
        igamma = 1.0
        ic = 1.0
    return c_fond * Nc * ic + q_sovraccarico * Nq * iq + 0.5 * gamma_fond * B_eff * Ngamma * igamma


def evaluate_ntc_combination(d: DatiMuro, df: pd.DataFrame, tipo: str, kh: float, kv: float, g_phi: float, g_stab: float, g_dest: float, g_q: float) -> Dict[str, float]:
    z, sig_h, Ph, Pv, zbar_h = integrate_pressures_ntc(df, d.H, d.falda_retro, d.q, d.delta_muro, kh, kv, g_phi, g_q, g_dest)
    zf, sig_p, Pp, z_pp = integrate_passive(df, min(d.h_fronte, d.H), d.falda_fronte, g_phi, g_stab, kh if d.include_passivo else 0.0)
    if not d.include_passivo:
        Pp, z_pp = 0.0, 0.0

    braccio_Ph_spiccato = max(d.H - zbar_h, 0.0)
    braccio_Ph_polo = d.t_base + braccio_Ph_spiccato
    braccio_Pp_polo = max(min(d.h_fronte, d.H) - z_pp, 0.0)

    W_base = d.B * d.t_base * d.gamma_cls * g_stab
    x_base = d.B / 2.0
    W_fusto = 0.5 * (d.t_fusto_top + d.t_fusto_bot) * d.H * d.gamma_cls * g_stab
    x_fusto = d.B_punta + (d.t_fusto_bot / 2.0)

    gam_eff = sigma_v_eff(df, d.H, d.falda_retro) / max(d.H, 1e-9)
    W_heel = d.B_tallone * d.H * gam_eff * g_stab
    x_heel = d.B_punta + d.t_fusto_bot + (d.B_tallone / 2.0)
    Wq = d.q * d.B_tallone * g_q
    x_q = x_heel

    F_base = kh * (W_base / g_stab)
    F_fusto = kh * (W_fusto / g_stab)
    F_heel = kh * (W_heel / g_stab)

    H_tirante, V_tirante, M_tirante_polo = 0.0, 0.0, 0.0
    H_tirante_spiccato, V_tirante_spiccato, M_tirante_spiccato = 0.0, 0.0, 0.0
    if d.ha_tirante:
        alpha_t = math.radians(d.t_inclinazione)
        H_tirante = d.t_tiro * math.cos(alpha_t)
        V_tirante = d.t_tiro * math.sin(alpha_t)
        x_tirante_testa = d.B_punta + d.t_fusto_bot
        M_tirante_polo = H_tirante * d.t_quota + V_tirante * x_tirante_testa

        y_spiccato = d.t_base
        if d.t_quota > y_spiccato:
            H_tirante_spiccato = H_tirante
            V_tirante_spiccato = V_tirante
            M_tirante_spiccato = H_tirante_spiccato * (d.t_quota - y_spiccato)

    V_tot = (W_base + W_fusto + W_heel + Wq) * (1.0 - kv) + Pv + V_tirante
    H_tot = Ph + F_base + F_fusto + F_heel - H_tirante

    M_stab = W_base * x_base + W_fusto * x_fusto + W_heel * x_heel + Wq * x_q + Pp * braccio_Pp_polo + Pv * d.B + M_tirante_polo
    M_destab = Ph * braccio_Ph_polo + F_base * (d.t_base / 2) + F_fusto * (d.t_base + d.H / 2) + F_heel * (d.t_base + d.H / 2)

    FS_rib = M_stab / max(M_destab, 1e-9)

    cu_base = float(df.iloc[-1]["cu_kPa"]) / g_phi
    Rf = d.mu_base * V_tot + cu_base * d.B + Pp
    FS_scorr = Rf / max(H_tot, 1e-9)

    M_net = max(M_destab - M_stab, 0) + (V_tot * d.B / 2.0)
    e = abs(M_net / max(V_tot, 1e-9) - d.B / 2.0)
    B_eff = d.B - 2 * e

    q_med = V_tot / d.B
    qmax = q_med * (1 + 6 * e / d.B)
    qmin = q_med * (1 - 6 * e / d.B)
    if qmin < 0:
        u = d.B / 2.0 - e
        qmax = (2.0 * V_tot) / (3.0 * u) if u > 0 else 0.0
        qmin = 0.0

    lay_fond = df.iloc[-1]
    phi_f = float(lay_fond["phi_deg"]) / g_phi
    c_f = float(lay_fond["cu_kPa"]) / g_phi
    gamma_f = float(lay_fond["gamma_dry"])
    q_sovraccarico_fond = d.h_fronte * gamma_f

    q_lim = calcola_qlim_hansen(B_eff, V_tot, max(H_tot, 0), gamma_f, phi_f, c_f, q_sovraccarico_fond)
    FS_portanza = q_lim / max(qmax, 1e-9)
    rapporto_q_amm = qmax / max(d.q_amm, 1e-9)

    N_spiccato = (W_fusto * (1.0 - kv)) + Pv + V_tirante_spiccato
    V_spiccato = Ph + F_fusto - H_tirante_spiccato
    M_spiccato = (Ph * braccio_Ph_spiccato) + (F_fusto * (d.H / 2.0)) - M_tirante_spiccato

    return {
        "Tipo": tipo,
        "Pa": Ph,
        "Pp": Pp,
        "FS_rib": FS_rib,
        "FS_scorr": FS_scorr,
        "qmax": qmax,
        "qmin": qmin,
        "q_lim": q_lim,
        "FS_portanza": FS_portanza,
        "q_amm_ratio": rapporto_q_amm,
        "N_spiccato": N_spiccato,
        "V_spiccato": V_spiccato,
        "M_spiccato": M_spiccato,
        "z_a": z,
        "sig_a": sig_h,
        "z_p": zf,
        "sig_p": sig_p,
    }


def calcola_muro(d: DatiMuro) -> Dict[str, object]:
    df, _ = parse_stratigrafia(d.stratigrafia_csv)
    st_EQU = evaluate_ntc_combination(d, df, "Statica (EQU)", 0.0, 0.0, 1.25, 0.9, 1.1, 1.5)
    st_GEO = evaluate_ntc_combination(d, df, "Statica (GEO)", 0.0, 0.0, 1.25, 1.0, 1.0, 1.3)
    se_pos = evaluate_ntc_combination(d, df, "Sismica kv+", d.kh, d.kv, 1.25, 1.0, 1.0, 1.0)
    se_neg = evaluate_ntc_combination(d, df, "Sismica kv-", d.kh, -d.kv, 1.25, 1.0, 1.0, 1.0)
    return {"stratigrafia": df, "statico": st_GEO, "sismico": se_pos, "st_EQU": st_EQU, "se_neg": se_neg}


def proprieta_equivalenti_pendio(df: pd.DataFrame, profondita: float) -> Dict[str, float]:
    total = min(profondita, float(df["z_bot_m"].max()))
    if total <= 0:
        row = df.iloc[0]
        return {
            "gamma_dry": float(row["gamma_dry"]),
            "gamma_sat": float(row["gamma_sat"]),
            "phi_deg": float(row["phi_deg"]),
            "cu_kPa": float(row["cu_kPa"]),
        }
    accum = {"gamma_dry": 0.0, "gamma_sat": 0.0, "phi_deg": 0.0, "cu_kPa": 0.0}
    used = 0.0
    for _, row in df.iterrows():
        h = min(float(row["z_bot_m"]), total) - float(row["z_top_m"])
        if h <= 0:
            continue
        used += h
        for key in accum:
            accum[key] += h * float(row[key])
    if used <= 0:
        used = 1.0
    return {key: value / used for key, value in accum.items()}


def profilo_pendio(H: float, beta_deg: float, berma: float) -> Tuple[np.ndarray, np.ndarray]:
    run = H / math.tan(math.radians(beta_deg))
    x = np.array([0.0, run, run + berma])
    y = np.array([0.0, H, H])
    return x, y


def quota_superficie_pendio(x: np.ndarray, H: float, beta_deg: float, berma: float) -> np.ndarray:
    run = H / math.tan(math.radians(beta_deg))
    y = np.zeros_like(x, dtype=float)
    mask_slope = (x >= 0) & (x <= run)
    y[mask_slope] = x[mask_slope] * math.tan(math.radians(beta_deg))
    mask_crest = x > run
    y[mask_crest] = H
    return y


def punto_superficie_pendio(x: float, H: float, beta_deg: float, berma: float) -> Tuple[float, float]:
    y = float(quota_superficie_pendio(np.array([x]), H, beta_deg, berma)[0])
    return x, y


def cerca_intersezioni_cerchio_superficie(cx: float, cy: float, r: float, H: float, beta_deg: float, berma: float, n: int = 900) -> List[float]:
    run = H / math.tan(math.radians(beta_deg))
    x_max = run + berma
    xs = np.linspace(0, x_max, n)
    surf = quota_superficie_pendio(xs, H, beta_deg, berma)
    inside = r**2 - (xs - cx) ** 2
    circle = np.full_like(xs, np.nan, dtype=float)
    valid = inside >= 0
    circle[valid] = cy - np.sqrt(inside[valid])
    diff = surf - circle
    intersections: List[float] = []
    for i in range(len(xs) - 1):
        if np.isnan(diff[i]) or np.isnan(diff[i + 1]):
            continue
        if diff[i] == 0:
            intersections.append(float(xs[i]))
        elif diff[i] * diff[i + 1] < 0:
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = diff[i], diff[i + 1]
            xr = x0 - y0 * (x1 - x0) / (y1 - y0)
            intersections.append(float(xr))
    deduped: List[float] = []
    for value in intersections:
        if not deduped or abs(value - deduped[-1]) > max(x_max / n * 3, 0.03):
            deduped.append(value)
    return deduped


def valuta_cerchio_fellenius(
    cx: float,
    cy: float,
    r: float,
    H: float,
    beta_deg: float,
    berma: float,
    props: Dict[str, float],
    falda_depth: float,
    kh: float = 0.0,
    slices: int = 24,
) -> Dict[str, object] | None:
    intersections = cerca_intersezioni_cerchio_superficie(cx, cy, r, H, beta_deg, berma)
    if len(intersections) < 2:
        return None
    x_left, x_right = intersections[0], intersections[-1]
    if x_right - x_left < 0.8:
        return None

    dx = (x_right - x_left) / slices
    resisting = 0.0
    driving = 0.0
    slice_rows = []
    for i in range(slices):
        xa = x_left + i * dx
        xb = xa + dx
        xm = 0.5 * (xa + xb)
        surface_y = float(quota_superficie_pendio(np.array([xm]), H, beta_deg, berma)[0])
        inside = r**2 - (xm - cx) ** 2
        if inside <= 0:
            return None
        slip_y = cy - math.sqrt(inside)
        height = surface_y - slip_y
        if height <= 0:
            return None
        dy_dx = -(xm - cx) / max(math.sqrt(inside), 1e-9)
        alpha = math.atan(dy_dx)
        base_len = dx / max(math.cos(alpha), 1e-6)
        z_water = max(surface_y - falda_depth, slip_y)
        water_head = max(z_water - slip_y, 0.0)
        gamma = props["gamma_sat"] if water_head > 0 else props["gamma_dry"]
        weight = gamma * height * dx
        u = GAMMA_W * water_head
        normal_eff = max(weight * math.cos(alpha) - kh * weight * abs(math.sin(alpha)) - u * base_len, 0.0)
        shear_drive = abs(weight * math.sin(alpha)) + kh * weight * max(math.cos(alpha), 0.0)
        shear_res = props["cu_kPa"] * base_len + normal_eff * math.tan(math.radians(props["phi_deg"]))
        resisting += shear_res
        driving += shear_drive
        slice_rows.append(
            {
                "x": xm,
                "y_surface": surface_y,
                "y_slip": slip_y,
                "alpha_deg": math.degrees(alpha),
                "W": weight,
                "S_res": shear_res,
                "S_drive": shear_drive,
            }
        )

    if driving <= 0:
        return None
    fs = resisting / driving
    return {
        "FS": fs,
        "center": (cx, cy),
        "radius": r,
        "x_left": x_left,
        "x_right": x_right,
        "slices": pd.DataFrame(slice_rows),
        "intersections": intersections,
    }


def analisi_stabilita_pendio(d: DatiMuro, df: pd.DataFrame) -> Dict[str, object]:
    props = proprieta_equivalenti_pendio(df, d.pendio_H)
    run = d.pendio_H / math.tan(math.radians(d.pendio_beta))
    crest_x = run
    x_max = crest_x + d.pendio_berma
    best_static = None
    best_seismic = None

    entry_points = np.linspace(0.05 * crest_x, 0.92 * crest_x, 10)
    exit_points = np.linspace(crest_x * 0.78, x_max, 12)
    offsets = np.linspace(d.pendio_H * 0.35, d.pendio_H * 2.0, 12)

    for x_entry in entry_points:
        p1 = np.array(punto_superficie_pendio(float(x_entry), d.pendio_H, d.pendio_beta, d.pendio_berma))
        for x_exit in exit_points:
            if x_exit <= x_entry + 0.8:
                continue
            p2 = np.array(punto_superficie_pendio(float(x_exit), d.pendio_H, d.pendio_beta, d.pendio_berma))
            chord = p2 - p1
            chord_len = float(np.linalg.norm(chord))
            if chord_len <= 0.5:
                continue
            midpoint = 0.5 * (p1 + p2)
            normal = np.array([-chord[1], chord[0]]) / chord_len
            if normal[1] < 0:
                normal = -normal

            for offset in offsets:
                center = midpoint + normal * offset
                cx, cy = float(center[0]), float(center[1])
                r = float(np.linalg.norm(center - p1))
                if cy <= d.pendio_H * 0.6:
                    continue
                trial_static = valuta_cerchio_fellenius(cx, cy, r, d.pendio_H, d.pendio_beta, d.pendio_berma, props, d.falda_retro, 0.0)
                if trial_static and (best_static is None or trial_static["FS"] < best_static["FS"]):
                    best_static = trial_static
                trial_seis = valuta_cerchio_fellenius(cx, cy, r, d.pendio_H, d.pendio_beta, d.pendio_berma, props, d.falda_retro, d.kh)
                if trial_seis and (best_seismic is None or trial_seis["FS"] < best_seismic["FS"]):
                    best_seismic = trial_seis

    return {
        "props": props,
        "profilo": profilo_pendio(d.pendio_H, d.pendio_beta, d.pendio_berma),
        "statico": best_static,
        "sismico": best_seismic,
    }


def figura_pendio(d: DatiMuro, pendio: Dict[str, object]) -> go.Figure:
    x_prof, y_prof = pendio["profilo"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=np.r_[x_prof[0], x_prof, x_prof[-1], x_prof[0]],
            y=np.r_[0.0, y_prof, 0.0, 0.0],
            fill="toself",
            fillcolor="rgba(184, 146, 92, 0.45)",
            line=dict(color="#6B4F2A", width=2),
            name="Pendio",
        )
    )
    water_y = d.pendio_H - d.falda_retro
    if 0 < water_y < d.pendio_H:
        fig.add_trace(
            go.Scatter(
                x=[0, x_prof[-1]],
                y=[water_y, water_y],
                mode="lines",
                line=dict(color="#2B83BA", width=2, dash="dot"),
                name="Falda",
            )
        )
    for label, color in [("statico", "#0F766E"), ("sismico", "#B45309")]:
        result = pendio[label]
        if not result:
            continue
        cx, cy = result["center"]
        r = result["radius"]
        xs = np.linspace(result["x_left"], result["x_right"], 220)
        ys = cy - np.sqrt(np.maximum(r**2 - (xs - cx) ** 2, 0.0))
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=3), name=f"Superficie critica {label}"))
        fig.add_trace(go.Scatter(x=[cx], y=[cy], mode="markers", marker=dict(color=color, size=8), name=f"Centro {label}"))
    fig.update_layout(
        title="Stabilita del pendio - cerchio critico",
        template="plotly_white",
        xaxis_title="x [m]",
        yaxis_title="y [m]",
        legend=dict(orientation="h", y=-0.18),
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def tabella_sintesi(d: DatiMuro, r: Dict[str, object]) -> pd.DataFrame:
    st = r["statico"]
    se = r["sismico"]
    rows = [
        ("Pa (Spinta Orizz.) [kN/m]", st["Pa"], se["Pa"]),
        ("Pp (Spinta Passiva) [kN/m]", st["Pp"], se["Pp"]),
        ("FS Ribaltamento [-]", r["st_EQU"]["FS_rib"], se["FS_rib"]),
        ("FS Scorrimento [-]", st["FS_scorr"], se["FS_scorr"]),
        ("q_max [kPa]", st["qmax"], se["qmax"]),
        ("q_max / q_amm [-]", st["q_amm_ratio"], se["q_amm_ratio"]),
        ("q_lim Hansen [kPa]", st["q_lim"], se["q_lim"]),
        ("FS Portanza [-]", st["FS_portanza"], se["FS_portanza"]),
    ]
    return pd.DataFrame(rows, columns=["Parametro", "Statico (GEO/EQU)", "Sismico kv+"])


def tabella_sollecitazioni(r: Dict[str, object]) -> pd.DataFrame:
    rows = []
    for k in ["statico", "sismico", "st_EQU", "se_neg"]:
        data = r[k]
        rows.append(
            {
                "Combinazione": data["Tipo"],
                "N Spiccato [kN/m]": round(data["N_spiccato"], 2),
                "V Spiccato [kN/m]": round(data["V_spiccato"], 2),
                "M Spiccato [kNm/m]": round(data["M_spiccato"], 2),
            }
        )
    return pd.DataFrame(rows)


def genera_warning(d: DatiMuro, r: dict) -> List[str]:
    warnings = []
    st_EQU = r["st_EQU"]
    st_GEO = r["statico"]
    se = r["sismico"]
    if st_EQU["FS_rib"] < 1.0:
        warnings.append(f"FS ribaltamento statico (EQU) non soddisfatto ({st_EQU['FS_rib']:.2f} < 1.0)")
    if st_GEO["FS_scorr"] < 1.0:
        warnings.append(f"FS scorrimento statico (GEO) non soddisfatto ({st_GEO['FS_scorr']:.2f} < 1.0)")
    if st_GEO["FS_portanza"] < 1.0:
        warnings.append(f"FS portanza statica non soddisfatto ({st_GEO['FS_portanza']:.2f} < 1.0)")
    if st_GEO["q_amm_ratio"] > 1.0:
        warnings.append(f"q_max statica supera q_amm ({st_GEO['qmax']:.1f} > {d.q_amm:.1f} kPa)")
    if se["FS_rib"] < 1.0:
        warnings.append(f"FS ribaltamento sismico non soddisfatto ({se['FS_rib']:.2f} < 1.0)")
    if se["FS_scorr"] < 1.0:
        warnings.append(f"FS scorrimento sismico non soddisfatto ({se['FS_scorr']:.2f} < 1.0)")
    if se["FS_portanza"] < 1.0:
        warnings.append(f"FS portanza sismica non soddisfatto ({se['FS_portanza']:.2f} < 1.0)")
    if se["q_amm_ratio"] > 1.0:
        warnings.append(f"q_max sismica supera q_amm ({se['qmax']:.1f} > {d.q_amm:.1f} kPa)")
    return warnings


def genera_note(d: DatiMuro, r: dict) -> List[str]:
    note = []
    if d.include_passivo:
        note.append("Il contributo passivo a fronte e incluso nel calcolo.")
    if d.ha_tirante:
        note.append("E presente un tirante di ancoraggio: l'equilibrio e le sollecitazioni strutturali beneficiano delle componenti stabilizzanti.")
    note.append("Carico limite: la capacita portante e calcolata con la formula trinomia di Brinch-Hansen.")
    note.append(f"q_amm di riferimento inserita: {d.q_amm:.1f} kPa.")
    return note


def figura_geometria(d: DatiMuro) -> go.Figure:
    fig = go.Figure()
    H_tot = d.t_base + d.H
    xf = d.B_punta
    xft = xf + d.t_fusto_bot
    x_muro = [0, d.B, d.B, xft, xf + d.t_fusto_top, xf, xf, 0, 0]
    y_muro = [0, 0, d.t_base, d.t_base, H_tot, H_tot, d.t_base, d.t_base, 0]

    fig.add_trace(go.Scatter(x=x_muro, y=y_muro, fill="toself", fillcolor="lightgray", name="Muro (cls)", line=dict(color="black", width=1.5)))
    fig.add_trace(go.Scatter(x=[xft, d.B, d.B + 2, xft], y=[d.t_base, d.t_base, H_tot, H_tot], fill="toself", fillcolor="tan", name="Terreno a tergo", line=dict(color="sienna", width=1)))

    if d.h_fronte > 0:
        hf = min(d.h_fronte, d.H)
        fig.add_trace(go.Scatter(x=[0, xf, xf, 0], y=[d.t_base, d.t_base, d.t_base + hf, d.t_base + hf], fill="toself", fillcolor="peru", name="Terreno a fronte", line=dict(color="saddlebrown", width=1)))

    if d.falda_retro < d.H:
        y_falda = d.t_base + d.falda_retro
        fig.add_trace(go.Scatter(x=[xft, d.B, d.B + 2, xft], y=[y_falda, y_falda, H_tot, H_tot], fill="toself", fillcolor="rgba(0, 100, 220, 0.20)", name="Zona satura", line=dict(color="blue", width=1, dash="dot")))

    if d.ha_tirante:
        x_start = xf + d.t_fusto_bot
        y_start = d.t_base + d.t_quota
        alpha_rad = math.radians(d.t_inclinazione)
        lunghezza_grafica = 2.0
        x_end = x_start + lunghezza_grafica * math.cos(alpha_rad)
        y_end = y_start - lunghezza_grafica * math.sin(alpha_rad)
        fig.add_trace(go.Scatter(x=[x_start, x_end], y=[y_start, y_end], mode="lines+markers", name="Tirante", line=dict(color="red", width=2, dash="dash"), marker=dict(symbol="arrow-bar-up", size=10)))

    fig.update_layout(title="Modello fisico e tiranti", xaxis_title="x [m]", yaxis_title="y [m]", template="plotly_white", legend=dict(orientation="h", y=-0.15))
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def figura_output(r: Dict[str, object]) -> go.Figure:
    st_res = r["statico"]
    se = r["sismico"]
    ha_passivo = st_res["Pp"] > 0 or se["Pp"] > 0

    if ha_passivo:
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Pressioni attive a tergo", "Pressioni passive a fronte"), shared_yaxes=False)
    else:
        fig = make_subplots(rows=1, cols=1, subplot_titles=("Pressioni attive a tergo",))

    fig.add_trace(go.Scatter(x=st_res["sig_a"], y=st_res["z_a"], mode="lines", fill="tozerox", name="Attiva statica", line=dict(color="royalblue"), fillcolor="rgba(65, 105, 225, 0.20)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=se["sig_a"], y=se["z_a"], mode="lines", name="Attiva sismica", line=dict(color="firebrick", dash="dash")), row=1, col=1)

    if ha_passivo:
        fig.add_trace(go.Scatter(x=st_res["sig_p"], y=st_res["z_p"], mode="lines", fill="tozerox", name="Passiva statica", line=dict(color="seagreen"), fillcolor="rgba(46, 139, 87, 0.20)"), row=1, col=2)
        fig.add_trace(go.Scatter(x=se["sig_p"], y=se["z_p"], mode="lines", name="Passiva sismica", line=dict(color="darkorange", dash="dash")), row=1, col=2)
        fig.update_yaxes(title_text="z fronte [m]", autorange="reversed", row=1, col=2)

    fig.update_yaxes(title_text="z tergo [m]", autorange="reversed", row=1, col=1)
    fig.update_layout(title="Diagrammi delle pressioni", template="plotly_white", legend=dict(orientation="h", y=-0.18))
    return fig
