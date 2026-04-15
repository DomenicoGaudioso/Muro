{
  "meta": {
    "verifica": "Verifica sismica pseudo-statica (metodo Mononobe-Okabe)",
    "norma": "NTC2018 §7.11.5 / EC8-5 §7.3.2.2 / Mononobe-Okabe 1929",
    "fonte": "NTC2018 §7.11.5 — Muri di sostegno in zona sismica. Coefficienti kh e kv secondo NTC2018 Tab. 7.11.I",
    "url_fonte": "https://www.ntc.gov.it/images/documenti/NTC_2018_GU_1_21_feb_2018.pdf",
    "data_generazione": "2026-04-15",
    "autore": "CivilBox Test Builder Agent"
  },
  "input": {
    "H": 5.0,
    "q": 10.0,
    "gamma_cls": 24.0,
    "B": 3.5,
    "B_punta": 1.0,
    "B_tallone": 2.5,
    "t_base": 0.5,
    "t_fusto_top": 0.3,
    "t_fusto_bot": 0.5,
    "mu_base": 0.55,
    "q_amm": 250.0,
    "h_fronte": 0.5,
    "falda_retro": 99.0,
    "falda_fronte": 99.0,
    "kh": 0.15,
    "kv": 0.05,
    "delta_muro": 20.0,
    "include_passivo": true,
    "ha_tirante": false,
    "stratigrafia_csv": "10.0,18,20,30,0,25000"
  },
  "risultati_attesi": {
    "FS_rib_sismico": {
      "valore": 2.4004,
      "unita": "-",
      "tolleranza_percentuale": 1.0,
      "nota": "FS ribaltamento in condizione sismica (kh=0.15, kv=0.05) — da confrontare con limite NTC2018: ≥1.0 per combinazione sismica"
    },
    "FS_scorr_sismico": {
      "valore": 1.2248,
      "unita": "-",
      "tolleranza_percentuale": 1.0,
      "nota": "FS scorrimento in condizione sismica — riduzione rispetto al caso statico per effetto forze inerziali"
    },
    "Pa_sismico": {
      "valore": 121.9425,
      "unita": "kN/m",
      "tolleranza_percentuale": 1.0,
      "nota": "Spinta attiva sismica orizzontale (Mononobe-Okabe) — incremento rispetto a caso statico (84 kN/m ca.)"
    }
  },
  "esito_atteso": "VERIFICATO",
  "note_test": "Verifica che il coefficiente di spinta Ka_MO sia calcolato correttamente con angolo θ=atan(kh/(1-kv))=atan(0.15/0.95)=8.97°. La riduzione delle forze stabilizzanti verticali del fattore (1-kv) deve essere applicata."
}
