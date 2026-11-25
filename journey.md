# Diario delle prove

Le prove fatte finora, in ordine. Lo stato del progetto e le decisioni aperte sono in `status.md`.

## 23 novembre: pre-test sulla pipeline testuale del paper

Prima di scrivere l'estensione volevamo sapere se l'agente del paper, così com'è, riesce già a rispondere su reperti e siti sommersi. Il codice della base non è stato modificato.

### Configurazione

- LLM: gpt-oss:20b su Ollama locale, come job SLURM su blackhole (RTX 4060 + GTX TITAN X), temperatura 0,1, reasoning effort low. Il paper usava Ollama Cloud: i pesi sono gli stessi, ma l'esecuzione no.
- Script: `evaluation/evaluate.py` e `evaluation/evaluate_multiturn.py` del paper, lanciati da `eval/underwater/evaluate_underwater.py` e `eval/underwater/evaluate_multiturn_underwater.py`. I wrapper cambiano solo i seed, i template delle domande e la cartella di output; tutte le funzioni (agente, baseline senza tool, memoria, punteggi, CSV) sono quelle del paper.
- Un'unica deviazione: `MIN_RECORDS = 0`. Con il valore del paper (almeno 2 record dal tool) degli 11 seed passava solo "Antonia Augusta", e solo perché Europeana ha delle monete con Antonia come autorità emittente.

Gli 11 seed: Ulysses of Punta Epitaffio, Antonia Augusta, Dionysus with ivy wreath, Artemision Bronze, Jockey of Artemision, Antikythera Youth, Antikythera Philosopher, Punta Epitaffio nymphaeum, Baia underwater park, Portus Julius, Miseno harbour.

### Valutazione principale

Tre domande per seed, con gli stessi tre tipi del paper adattati a oggetti e siti: "Tell me about X." (identificazione), "Where was X found?" (provenienza), "When does X date from?" (datazione). 33 domande in tutto, ciascuna posta all'agente con il tool e allo stesso LLM senza tool.

| Metrica | Agente | Senza tool |
|---|---|---|
| tool chiamato | 100% | |
| almeno un URL Europeana nella risposta | 21,2% | |
| almeno un anno nella risposta | 27,3% | 30,3% |
| anni fuori da ±2 dai record (temporal grounding violations) | 0% | 0% |

File: `eval/underwater/results/results_20261123_212201.csv` (non versionato).

### Multi-turno

Gli scenari A, B e C del paper con domande da patrimonio sommerso:

- A, riferimento implicito: "Tell me about X." → "When does it date from?" → "Where was it found?"
- B, cambio di oggetto: "Tell me about X1." → "Tell me about X2."
- C, dall'oggetto al sito: "Where was X found?" → "What else is known about that site?"

| Metrica | Valore |
|---|---|
| CRR (il nome resta nella query nei turni 2 e 3 di A) | 90,9% (20/22) |
| SIR (nel turno 2 di B la query contiene X2 e non X1) | 90,9% (10/11) |
| tool chiamato, per turno | 98,7% (76/77) |
| almeno un URL Europeana, per turno | 24,7% (19/77) |

33 sessioni, 77 turni. Il riepilogo stampato dal codice del paper dice "45 sessions": è un testo fisso. File: `eval/underwater/results/results_multiturn_20261123_213757.csv`.

### Cosa abbiamo visto leggendo le risposte

Le metriche del paper controllano la meccanica (il tool viene chiamato, il nome passa da un turno all'altro, c'è un URL), non il contenuto. Su questo gruppo danno numeri alti anche quando le risposte sono sbagliate.

Il tool del paper cerca un artista: estrae un nome, filtra con `who:` e tiene i record il cui autore contiene quel nome. Con oggetti e siti non trova niente, oppure trova cose che con l'oggetto non c'entrano, e il prompt chiede comunque all'LLM una biografia. Ne vengono fuori risposte come "Ulysses of Punta Epitaffio è un artista contemporaneo italiano", "il Jockey of Artemision è un celebre scultore greco del periodo arcaico" o "Antonia Augusta è una figura storica dell'antica Grecia, nota come autorità emittente di moneta". Le risposte che risultano "con fonte" citano record sbagliati: le monete per Antonia, o record non pertinenti per il Fantino.

Anche l'LLM senza tool inventa: per lui Antonia Augusta è una pittrice tedesca nata a Monaco nel 1843, e "Dionysus with ivy wreath" un dipinto del Rinascimento.

La violazione temporale a 0% non vuol dire che le date siano giuste. La regex del paper riconosce solo gli anni dal 1000 al 2029, quindi le date antiche del gruppo (età imperiale, V secolo a.C.) non vengono mai confrontate.

In due prove esplorative fatte prima, con domande in italiano, era uscito lo stesso quadro: "Baia" trattata come nome di uno scultore (il filtro sull'autore accetta un pittore rumeno, Traian Baia, e record di Baia Mare), Miseno "in provincia di Salerno", e una volta l'LLM ha passato al tool la query "Bernini" per il Ninfeo di Punta Epitaffio, rispondendo che il ninfeo è un'opera di Bernini con le opere di Bernini come fonti.

### Limiti delle prove

- Gli script di valutazione del paper cercano i marcatori `<<<ANSWER>>>…<<<END>>>` e usano domande in inglese, mentre il prompt in questa repo è in italiano con `<<<RISPOSTA>>>…<<<FINE>>>` e `FONTI:`. Le risposte vengono comunque estratte (il codice ha un ripiego), ma la regressione del paper non si riproduce nelle condizioni originali finché non sappiamo quale prompt è stato usato.
- crewai installato è la 1.15, più recente di quella del paper.
- Un solo giro per configurazione: con temperatura 0,1 le risposte cambiano tra un giro e l'altro.

### Cosa ne segue

Per valutare l'estensione servono, oltre alle metriche del paper, due controlli a mano: i dati presenti nella risposta ma non nelle schede recuperate, e le domande con premessa falsa. Il prossimo passo è lo stadio 4 su ArCo per il percorso testuale, da confrontare con la stessa batteria di domande a flag spento e acceso.

## 23 novembre: indice di immagini, prime verifiche

Indice costruito da `curated_group.csv` con EmbeddingGemma 2 (budget 280): 42 viste di catalogo per 13 elementi. Ogni vista usata come query ritrova il proprio oggetto (42/42).

I punteggi sono molto vicini tra loro: viste dello stesso oggetto tra 0,72 e 0,97 (mediana 0,87), oggetti diversi fino a 0,93 (Efebo di Anticitera contro Zeus di Artemisio). Una foto del Bronzo A di Riace, che nell'indice non c'è, viene presa per l'Efebo di Anticitera con 0,916 e un distacco di 0,04 dal secondo. Con queste distanze una soglia sul solo punteggio massimo non basta a rifiutare: soglia e margine vanno tarati su un validation set, e i bronzi non indicizzati vanno tra i negativi difficili.
