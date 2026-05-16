# -*- coding: utf-8 -*-
"""
Test del solver Muro — verifiche geotecniche Brinch-Hansen, ribaltamento, scorrimento.

Verifica i fattori di capacità portante, i rapporti di sicurezza FS_rib e FS_scorr
e la spinta attiva Mononobe-Okabe su casi analitici verificabili.
Dati conformi NTC2018, geometrie realistiche da cantiere.
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from src import (
    ka_mo,
    kp,
    fattori_capacita_portante,
    calcola_qlim_hansen,
    parse_stratigrafia,
    evaluate_ntc_combination,
    DatiMuro,
    calcola_muro,
)

GAMMA_W = 9.81

# Stratigrafia sabbia per le verifiche del muro
STRAT_SABBIA = "10.0,18,20,30,0,25000"


def test_ka_mo_coincide_rankine_senza_sisma():
    """Ka Mononobe-Okabe senza sisma deve coincidere con Rankine (δ=0).

    Per kh=0, kv=0, δ=0: Ka_MO = Ka_Rankine = (1-sinφ)/(1+sinφ).
    """
    phi = 30.0
    Ka_mo_val = ka_mo(phi, 0.0, 0.0, 0.0)
    Ka_rankine = (1 - math.sin(math.radians(phi))) / (1 + math.sin(math.radians(phi)))
    assert abs(Ka_mo_val - Ka_rankine) < 0.005, (
        f"Ka_MO={Ka_mo_val:.4f} vs Ka_Rankine={Ka_rankine:.4f}"
    )


def test_kp_rankine_phi30():
    """Kp Rankine per φ=30°: Kp = (1+sin30)/(1-sin30) = 3.0."""
    Kp = kp(30.0)
    assert abs(Kp - 3.0) < 0.001, f"Kp(30°) = {Kp:.4f}, atteso 3.0"


def test_fattori_capacita_portante_nq_nc():
    """Fattori di capacità portante Brinch-Hansen per φ=30°.

    Nc = (Nq-1)/tanφ, Nq = exp(π tanφ)×tan²(45+φ/2).
    Valori tipici per φ=30°: Nq ≈ 18.4, Nc ≈ 30.1, Nγ ≈ 22.4.
    """
    Nc, Nq, Ngamma = fattori_capacita_portante(30.0)
    # Nq = exp(π×tan30)×tan²(60°)
    Nq_atteso = math.exp(math.pi * math.tan(math.radians(30))) * math.tan(math.radians(60)) ** 2
    Nc_atteso = (Nq_atteso - 1) / math.tan(math.radians(30))
    assert abs(Nq - Nq_atteso) < 0.1, f"Nq={Nq:.2f}, atteso {Nq_atteso:.2f}"
    assert abs(Nc - Nc_atteso) < 0.5, f"Nc={Nc:.2f}, atteso {Nc_atteso:.2f}"
    assert Ngamma > 0, "Ngamma deve essere positivo per φ>0"


def test_fattori_phi_zero_argilla():
    """Fattori di capacità portante per φ=0 (argilla): Nc=5.14, Nq=1, Nγ=0."""
    Nc, Nq, Ngamma = fattori_capacita_portante(0.0)
    assert abs(Nc - 5.14) < 0.01, f"Nc(φ=0) = {Nc:.3f}, atteso 5.14"
    assert abs(Nq - 1.0) < 0.01, f"Nq(φ=0) = {Nq:.3f}, atteso 1.0"
    assert abs(Ngamma) < 0.01, f"Nγ(φ=0) = {Ngamma:.3f}, atteso 0.0"


def test_calcola_qlim_hansen_sabbia():
    """Capacità portante di Brinch-Hansen per fondazione in sabbia φ=30°.

    B=2m, V=200 kN/m, H=0 (nessuna forza orizzontale), h_fronte=0.
    γ=18 kN/m³, q_sovracccarico=0.
    q_lim deve essere >> 0 e fisicamente coerente (>> γ×B/2).
    """
    Nc, Nq, Ngamma = fattori_capacita_portante(30.0)
    q_lim = calcola_qlim_hansen(
        B_eff=2.0, V_tot=200.0, H_tot=0.0,
        gamma_fond=18.0, phi_fond=30.0, c_fond=0.0,
        q_sovraccarico=0.0,
    )
    q_min_atteso = 0.5 * 18.0 * 2.0 * Ngamma  # solo termine Nγ
    assert q_lim >= q_min_atteso - 0.1, (
        f"q_lim = {q_lim:.1f} kPa deve essere >= {q_min_atteso:.1f} kPa"
    )
    assert q_lim > 100.0, f"q_lim = {q_lim:.1f} kPa troppo bassa per sabbia φ=30°"


def test_muro_fs_ribaltamento_positivo():
    """Muro di sostegno in equilibrio: FS_ribaltamento deve essere > 1.

    Caso fisico: muro H=4m, base B=3m, sabbia φ=30°.
    Il muro è dimensionato per avere FS_rib > 1.
    """
    d = DatiMuro(
        H=4.0, q=10.0, gamma_cls=25.0,
        B=3.0, B_punta=0.6, B_tallone=1.8,
        t_base=0.5, t_fusto_top=0.3, t_fusto_bot=0.4,
        mu_base=0.5, q_amm=200.0,
        h_fronte=0.5, falda_retro=100.0, falda_fronte=100.0,
        kh=0.0, kv=0.0,
        delta_muro=20.0, include_passivo=True,
        stratigrafia_csv=STRAT_SABBIA,
    )
    r = calcola_muro(d)
    FS_rib = r["st_EQU"]["FS_rib"]
    assert FS_rib > 1.0, f"FS ribaltamento = {FS_rib:.2f} deve essere > 1.0"


def test_muro_ka_mo_sisma_maggiore_statica():
    """Spinta attiva sismica (kh>0) deve essere maggiore di quella statica.

    Mononobe-Okabe: per kh>0 la spinta attiva aumenta.
    Ka_MO(kh>0) > Ka_Rankine.
    """
    phi = 30.0
    delta = 20.0
    Ka_stat = ka_mo(phi, delta, 0.0, 0.0)
    Ka_sis = ka_mo(phi, delta, 0.1, 0.05)
    assert Ka_sis > Ka_stat, (
        f"Ka_MO sismico={Ka_sis:.4f} deve essere > Ka_MO statico={Ka_stat:.4f}"
    )


def test_muro_fs_scorrimento():
    """FS scorrimento deve essere > 0 per qualsiasi configurazione valida.

    La resistenza allo scorrimento = μ×V_tot + c×B + Pp > 0.
    """
    d = DatiMuro(
        H=3.5, q=5.0, gamma_cls=25.0,
        B=2.8, B_punta=0.5, B_tallone=1.7,
        t_base=0.4, t_fusto_top=0.3, t_fusto_bot=0.4,
        mu_base=0.5, q_amm=150.0,
        h_fronte=0.3, falda_retro=100.0, falda_fronte=100.0,
        kh=0.0, kv=0.0,
        delta_muro=15.0, include_passivo=True,
        stratigrafia_csv=STRAT_SABBIA,
    )
    r = calcola_muro(d)
    FS_scorr = r["statico"]["FS_scorr"]
    assert FS_scorr > 0.0, f"FS scorrimento = {FS_scorr:.2f} deve essere > 0"


if __name__ == "__main__":
    tests = [
        test_ka_mo_coincide_rankine_senza_sisma,
        test_kp_rankine_phi30,
        test_fattori_capacita_portante_nq_nc,
        test_fattori_phi_zero_argilla,
        test_calcola_qlim_hansen_sabbia,
        test_muro_fs_ribaltamento_positivo,
        test_muro_ka_mo_sisma_maggiore_statica,
        test_muro_fs_scorrimento,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} test superati")
    sys.exit(failed)
