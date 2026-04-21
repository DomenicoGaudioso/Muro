# Muro di Sostegno - Analisi Statica e Sismica

Applicazione web basata su Streamlit per l'analisi geotecnica di muri di sostegno in calcestruzzo armato. Il progetto calcola spinte delle terre, verifiche a ribaltamento e scorrimento, pressioni di contatto, portanza e sollecitazioni strutturali allo spiccato.

## Funzionalita principali

- Analisi statica e sismica pseudo-statica
- Stratigrafie multistrato con tensioni efficaci e falda
- Contributo passivo a fronte opzionale
- Modellazione di tiranti di ancoraggio
- Grafici interattivi Plotly
- Export input JSON e relazioni Word/PDF

## Installazione

Richiede Python 3.10 o superiore.

```bash
pip install -r requirements.txt
```

## Avvio

```bash
streamlit run app.py
```

## Struttura essenziale

- `app.py`: entrypoint Streamlit
- `src.py`: motore di calcolo e grafici
- `src_report.py`: generazione relazioni
- `docs/DOCUMENTAZIONE.html`: documentazione sintetica

## Note tecniche

- `q_amm` viene confrontata con `q_max` nei controlli e nei warning.
- Le sollecitazioni strutturali mantengono il segno per una lettura tecnica corretta.
- L'export PDF richiede il pacchetto `fpdf2`.

## Disclaimer

I risultati devono essere verificati da un ingegnere abilitato prima di qualsiasi uso progettuale o autorizzativo.
