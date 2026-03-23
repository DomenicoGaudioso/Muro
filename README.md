# Muro di Sostegno - Analisi Statica e Sismica

Un'applicazione web interattiva basata su Streamlit per l'analisi e la verifica geotecnica di muri di sostegno in calcestruzzo armato. Il tool esegue calcoli di spinta delle terre, verifiche a ribaltamento e scorrimento, e controlli delle pressioni di contatto, integrando condizioni statiche, sismiche (metodo pseudo-statico) e la presenza di falde acquifere.

## 📌 Caratteristiche
* **Interfaccia Web Intuitiva:** Sviluppata in Streamlit per un inserimento dati rapido e visualizzazione dei risultati in tempo reale.
* **Analisi Multistrato:** Supporta stratigrafie complesse con calcolo automatico delle tensioni efficaci.
* **Verifiche Geotecniche:** Calcolo dei fattori di sicurezza per ribaltamento e scorrimento, sia in campo statico che sismico.
* **Visualizzazione Avanzata:** Generazione di grafici interattivi tramite Plotly per la geometria dell'opera e i diagrammi delle pressioni laterali.
* **Reportistica e Warning:** Generazione automatica di note tecniche interpretative e avvisi per verifiche critiche (es. FS < 1.5 in statico).
* **Import/Export:** Salvataggio e caricamento dei dati di input in formato JSON ed esportazione dei risultati in CSV.

## 📐 Principi Teorici e Modelli Matematici

Il software si basa su rigorosi modelli di meccanica delle terre per la valutazione delle spinte e la stabilità dell'opera.

* **Spinta Attiva (Teoria di Rankine):** La pressione orizzontale attiva a tergo del muro è valutata assumendo il raggiungimento dello stato di equilibrio limite attivo. Il coefficiente di spinta attiva è calcolato come $K_a = \frac{1 - \sin(\phi)}{1 + \sin(\phi)}$. La tensione orizzontale include il contributo della tensione verticale efficace, la pressione idrostatica e l'effetto del sovraccarico superficiale $q$.
* **Resistenza Passiva (Teoria di Rankine):** Il contributo stabilizzante del terreno a fronte del muro (se attivato) è modellato tramite il coefficiente di spinta passiva $K_p = \frac{1 + \sin(\phi)}{1 - \sin(\phi)}$.
* **Azione Sismica (Metodo Pseudo-Statico):** Gli effetti inerziali indotti dal sisma sono quantificati attraverso i coefficienti sismici orizzontale ($k_h$) e verticale ($k_v$). Le forze stabilizzanti verticali vengono ridotte del fattore $(1 - k_v)$, mentre le spinte orizzontali vengono incrementate di una quota proporzionale a $k_h \cdot \sigma'_v$.
* **Verifica a Ribaltamento:** Valutata rispetto al lembo estremo di valle (piede della fondazione). Il fattore di sicurezza è definito come $FS_{rib} = \frac{M_r}{M_o}$, dove $M_r$ è il momento stabilizzante e $M_o$ il momento ribaltante.
* **Verifica a Scorrimento:** La stabilità alla traslazione orizzontale è governata dal criterio di Mohr-Coulomb all'interfaccia fondazione-terreno: $FS_{scorr} = \frac{\mu \cdot V + c_u \cdot B + P_p}{P_a}$.
* **Pressioni di Contatto:** La distribuzione delle tensioni sul piano di posa è calcolata assumendo una fondazione infinitamente rigida e un comportamento elastico del terreno, utilizzando la formula di Navier (principio del nucleo centrale): $q_{max,min} = \frac{V}{B} \left(1 \pm \frac{6e}{B}\right)$.

## 📥 Input Attesi

L'applicazione richiede l'inserimento granulare dei seguenti parametri attraverso la sidebar:

* **Geometria:** Altezza del terreno a tergo ($H$), Base totale ($B$), dimensioni di punta e tallone, spessori del fusto e della base, e altezza del terreno a fronte.
* **Carichi e Resistenza:** Sovraccarico uniforme ($q$), peso di volume del calcestruzzo ($\gamma_{cls}$), coefficiente di attrito alla base ($\mu$) e capacità portante ammissibile ($q_{amm}$).
* **Sismica:** Coefficienti pseudo-statici $k_h$ e $k_v$.
* **Falda Acquifera:** Profondità della falda a tergo e a fronte rispetto al piano campagna.
* **Stratigrafia (CSV):** Spessore dello strato, peso di volume secco e saturo ($\gamma_{dry}, \gamma_{sat}$), angolo di attrito ($\phi$), coesione non drenata ($c_u$) e modulo di reazione ($k$).

## 📤 Output Generati

A seguito dell'elaborazione, l'app restituisce i seguenti risultati:

* **Metriche di Sintesi:** Valori numerici dei Fattori di Sicurezza (FS) a scorrimento e ribaltamento (statici e sismici), tensione massima ($q_{max}$) confrontata con quella ammissibile.
* **Tabelle Dati:** Dettaglio delle spinte risultanti ($P_a$, $P_p$) e riepilogo tabellare scaricabile in formato CSV.
* **Grafici:**
    * Un modello geometrico in scala del muro, comprensivo delle quote della falda.
    * Diagrammi delle pressioni laterali (attive e passive) calcolate lungo la profondità $z$.
* **Diagnostica:** Messaggi di allerta per instabilità (es. sollevamento della fondazione se $q_{min} < 0$) o note sul meccanismo di rottura dominante.

## ⚙️ Requisiti di Sistema e Installazione

Assicurarsi di avere Python 3.8+ installato. Le dipendenze necessarie per eseguire l'applicazione sono:

```bash
pip install streamlit pandas numpy plotly
```

## 🚀 Utilizzo

Per avviare l'applicazione in ambiente locale, eseguire il seguente comando dal terminale nella directory principale del progetto:

```bash
streamlit run app.py
```

Questo avvierà un server locale e aprirà automaticamente l'interfaccia dell'applicazione nel tuo browser predefinito. È possibile caricare un file JSON di configurazione precedentemente esportato o inserire i parametri manualmente nell'interfaccia.
