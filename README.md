# Muro di Sostegno - Analisi Statica e Sismica

![Muro di Sostegno](socialMuro.png)

Applicazione web basata su Streamlit per l'analisi geotecnica e strutturale di muri di sostegno a mensola. Il progetto calcola spinte del terreno, verifiche di stabilita del muro, pressioni di contatto, portanza, sollecitazioni allo spiccato e stabilita del pendio.

## Funzionalita principali

- Analisi statica e sismica pseudo-statica
- Stratigrafie multistrato con gestione della falda
- Verifiche a ribaltamento, scorrimento e portanza
- Calcolo delle sollecitazioni strutturali del fusto
- Modellazione di tiranti di ancoraggio
- Verifica di stabilita del pendio con ricerca del cerchio critico
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

- `app.py`: interfaccia Streamlit e dashboard
- `src.py`: motore di calcolo, verifiche e grafici
- `src_report.py`: generazione relazioni Word/PDF
- `docs/DOCUMENTAZIONE.html`: guida utente e documentazione tecnica

## Verifiche incluse

- Ribaltamento del muro
- Scorrimento alla base
- Pressioni di contatto e confronto con `q_amm`
- Portanza con formulazione di Brinch-Hansen
- Sollecitazioni N, V, M allo spiccato
- Stabilita del pendio in campo statico e sismico

## Note tecniche

- `q_amm` viene confrontata con `q_max` nei controlli e nei warning automatici.
- Le sollecitazioni strutturali mantengono il segno per una lettura tecnica corretta.
- L'export PDF richiede il pacchetto `fpdf2`.

## Documentazione

La guida completa e disponibile in:

- `docs/DOCUMENTAZIONE.html`

## Disclaimer

I risultati devono essere verificati da un ingegnere abilitato prima di qualsiasi uso progettuale, esecutivo o autorizzativo.
