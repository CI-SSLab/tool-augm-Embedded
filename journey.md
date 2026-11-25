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

## 25 novembre: stadio 4 ICCD acceso (`--iccd`)

Stessa batteria di domande e stessi script dei pre-test del 23 novembre, con `ENABLE_ICCD_FALLBACK=true`: quando la cascata Europeana trova meno di 2 record, il tool cerca tra le 68 schede ICCD con contesto subacqueo, e il prompt riceve un blocco in più (cerca il reperto o il sito, non un artista; cita le schede ICCD; se non trovi nulla non indicare luogo, epoca o autore). La metrica di aderenza conta anche gli URL del catalogo ICCD.

| Metrica | Flag spento (23/11) | Flag acceso (25/11) |
|---|---|---|
| tool chiamato | 100% | 100% |
| almeno una fonte citata | 21,2% | 48,5% |
| almeno un anno nella risposta (agente) | 27,3% | 36,4% |
| CRR | 90,9% | 95,5% |
| SIR | 90,9% | 100% |
| tool chiamato, per turno | 98,7% | 100% |
| almeno una fonte, per turno | 24,7% | 48,1% |

File: `eval/underwater/results/iccd/results_20261125_161123.csv` e `results_multiturn_20261125_162847.csv`.

Dove ArCo ha la scheda (Punta Epitaffio, Parco Sommerso di Baia, Miseno) le risposte cambiano davvero: non parlano più di un artista, riportano i dati della scheda (ninfeo di età imperiale, primo scavo di Nino Lamboglia nel 1959, strutture fino a 400 m dalla riva; parco di 176 ettari sul litorale di Bacoli e Pozzuoli; molo in gettata cementizia vicino al faro di Capo Miseno) e citano la scheda.

Restano tre problemi.

1. Dove la scheda non dice in che regione si trova il sito, l'LLM la inventa: Punta Epitaffio finisce "sul Mar Adriatico", "in provincia di Cosenza", "in provincia di Cagliari" e "nel Lazio" in quattro risposte diverse. La scheda ICCD l'indirizzo lo ha ("Italia, Campania, NA, Bacoli"), ma lo stadio 4 per ora non lo passa.
2. L'LLM mescola il dato con la conoscenza generale: per il Parco Sommerso dice "istituito nel 1987", mentre la scheda dice che nel 1987 sono iniziati gli interventi di tutela, e trasforma 176 ettari in "circa 80.000 mq" (sono due numeri diversi della scheda). La statua di Ulisse viene descritta con i dati del sito, come se fossero la stessa cosa.
3. Dove le fonti non hanno niente (Efebo e Filosofo di Anticitera, bronzi di Artemisio, Dioniso, Portus Julius) la regola aggiunta al prompt non viene rispettata: l'agente continua a dare luogo, epoca e materiale inventati ("artista contemporaneo italiano", "marmo di Carrara", Portus Julius "porto di Roma" o "in provincia di Caserta"). Antonia Augusta non arriva mai allo stadio 4, perché la cascata trova le monete.

Le metriche del paper salgono, ma per i casi senza fonte non migliora nulla, e dove la fonte c'è compaiono errori nuovi sui dettagli che la scheda non contiene. Un'istruzione nel prompt non basta a far rispettare la graceful degradation a gpt-oss-20b: andrebbe imposta in codice.

## 25 novembre, secondo giro: indirizzo ICCD e testo fisso senza fonti

Due modifiche dopo il primo giro con lo stadio 4: i record ICCD ora portano anche l'indirizzo della scheda ("Italia, Campania, NA, Bacoli"), e quando il tool torna senza record la risposta non la scrive più l'LLM. Un guardrail del Task di CrewAI la sostituisce con un testo fisso: l'oggetto non è nelle fonti consultate, quindi niente luogo, datazione, autore o materiale. Le due modifiche valgono solo con il flag acceso.

| Metrica | Flag spento (23/11) | Stadio 4 (25/11) | Stadio 4 + indirizzo + testo fisso |
|---|---|---|---|
| almeno una fonte citata | 21,2% | 48,5% | 45,5% |
| almeno un anno nella risposta (agente) | 27,3% | 36,4% | 21,2% |
| CRR | 90,9% | 95,5% | 95,5% |
| SIR | 90,9% | 100% | 90,9% |
| tool chiamato, per turno | 98,7% | 100% | 100% |
| almeno una fonte, per turno | 24,7% | 48,1% | 45,5% |

File: `eval/underwater/results/iccd/results_20261125_170800.csv` e `results_multiturn_20261125_172701.csv`.

Il testo fisso è scattato in 16 risposte su 33: tutte quelle sui bronzi di Artemisio e di Anticitera, su Portus Julius e una su Dioniso. In nessuna di queste compare più un dato inventato. Il calo dell'anno presente nella risposta viene da qui: chi non ha fonti non dà date, ed è il comportamento voluto.

Punta Epitaffio, il Parco Sommerso e Miseno ora sono collocati tutti a Bacoli, in provincia di Napoli. Il Parco non è più "istituito nel 1987": la risposta dice che gli interventi di tutela sono iniziati nel 1987, come la scheda.

Restano i casi in cui il tool restituisce record che non c'entrano, e lì il testo fisso non scatta. Per Antonia Augusta la cascata trova le monete con Antonia come autorità emittente, e l'LLM scrive per esempio che fu "la prima moglie di Claudio, 39-54 d.C.". Per Dioniso, in due risposte su tre l'LLM ha cercato solo "Dionysus" e il filtro sull'autore ha accettato iscrizioni d'album olandesi di persone che si chiamano Dionysus. Ulisse viene ancora descritto con i dati del sito, come se statua e sito fossero la stessa cosa. Questi casi richiedono di controllare se i record trovati parlano davvero dell'oggetto, che è il compito del tool immagine e della lettura per ID.

## 25 novembre: tool immagine e integrazione nell'agente

Il tool immagine prende la foto, cerca l'oggetto più simile nell'indice, decide fra match, ambiguo e nessun match, e legge le schede per identificativo: una chiamata a Europeana per gli oggetti, la query ArCo delle schede subacquee per i siti. All'LLM arriva solo il JSON con le schede, senza punteggi; punteggi e miniature compaiono nel pannello dei dettagli di Streamlit.

Nell'app la scelta fra percorso testuale e percorso con immagine la fa il codice: se c'è una foto, o se la domanda è un seguito sull'oggetto della foto precedente, si usa il tool immagine; una nuova domanda del tipo "Chi è..." torna al percorso del paper. Quando non c'è nessun match l'LLM non viene chiamato e la risposta è un testo fisso. Il blocco FONTI viene ricostruito dal codice con gli url delle schede, perché gpt-oss-20b lo ometteva in tutte le prove. Tutto questo è dietro `ENABLE_IMAGE_SEARCH`, spento di default; gli script di valutazione del paper non passano dall'app.

Prima prova con l'LLM, su foto che sono nell'indice o ne derivano (quindi non è ancora un test del riconoscimento):

| Foto e domanda | Esito |
|---|---|
| Ulisse con dominante blu-verde, "A che epoca risale?" | originale ellenistico, replica della metà del I secolo d.C. (circa 45), come nella scheda |
| seguito senza foto, "Da quale sito proviene?" | la scheda non indica il sito; il luogo indicato è Baia, senza dire se è il ritrovamento o il museo |
| Ulisse, "È la statua trovata a Pompei?" | riporta Baia dalla scheda e non conferma Pompei |
| rumore, "Cos'è?" | nessun match, testo fisso |
| scheda di Punta Epitaffio, "Che cos'è e dove si trova?" | ninfeo sommerso, scavo di Lamboglia del 1959, Bacoli, fino a 400 m dalla riva |

Nella risposta sulla premessa falsa l'LLM non dice in modo esplicito che Pompei è sbagliato: si limita a riportare Baia. Per Ulisse il collegamento con la scheda di Punta Epitaffio non passa ancora, perché va prima verificato a mano.

## 25 novembre: test del tool immagine su opere famose

Per vedere se il tool regge anche fuori dal subacqueo abbiamo costruito un secondo gruppo, separato da quello sommerso: le opere più note (per numero di voci Wikipedia, da Wikidata) degli artisti delle domande del paper. Un'opera entra nell'indice solo se Europeana ne ha il record dallo stesso museo che la possiede secondo Wikidata, con titolo e autore corrispondenti e senza stampe o foto tratte dall'opera. Così la verità non dipende dall'encoder che stiamo testando. Ne escono 34 opere di 25 artisti, quasi sempre con una sola foto. Gli italiani sono quasi assenti: Uffizi, chiese e musei romani non mandano i loro dipinti su Europeana. Un caso è da verificare: per "La città che sale" di Boccioni il record è della GAM di Torino e potrebbe essere uno studio.

Le foto di query vengono da Wikimedia Commons, quindi da una fonte diversa dall'indice, e nella repo ci sono solo gli url (`data/eval/famous_queries.csv`). Ogni opera ha la foto originale e tre versioni degradate in modo controllato: un dettaglio ritagliato, una foto storta su un muro grigio, luce calda con sfocatura e JPEG pesante. I negativi sono altre opere famose degli stessi artisti, non indicizzate: lo stesso stile, la stessa mano, ma un'altra opera. Ogni foto ha una domanda, a rotazione fra "cos'è", "chi l'ha realizzata", "a che anno risale" e una premessa falsa ("È un'opera di ...?").

| Insieme | Foto | Top-1 | Top-5 | Esiti con τ = 0,80 |
|---|---|---|---|---|
| originale Commons | 34 | 97,1% | 100% | 32 match giusti, 1 ambiguo giusto, 1 rifiuto sbagliato |
| luce calda e JPEG | 34 | 97,1% | 100% | 32 match giusti, 1 ambiguo, 1 match sbagliato |
| dettaglio ritagliato | 34 | 97,1% | 97,1% | 33 match giusti, 1 sbagliato |
| foto storta su muro | 34 | 97,1% | 97,1% | 32 match giusti, 1 ambiguo, 1 rifiuto sbagliato |
| negativi, stesso artista | 58 | — | — | 26 rifiuti giusti, 22 ambigui, 10 match sbagliati |

Il riconoscimento è molto buono anche con le degradazioni, ma 14 foto Commons su 34 sono quasi identiche alla foto dell'indice (coseno ≥ 0,95), perché il museo ha caricato la stessa scansione: quei casi sono facili. Il problema vero è il rifiuto. Con la soglia provvisoria di 0,80 il tool accetta più di metà dei negativi, cioè scambia un'altra opera dello stesso pittore per quella indicizzata. Alzando la soglia:

| τ | foto positive accettate | top-1 giusto fra le accettate | negativi accettati |
|---|---|---|---|
| 0,80 | 134 / 136 | 98,5% | 32 / 58 |
| 0,85 | 128 / 136 | 100% | 7 / 58 |
| 0,90 | 110 / 136 | 100% | 0 / 58 |

Per i dipinti una soglia fra 0,85 e 0,90 separa quasi del tutto i due casi. Non è detto che valga per le foto subacquee, dove i punteggi sono più bassi: τ va tarato sul validation set del subacqueo, come previsto, e questo test va riportato come controllo di generalità. File: `eval/famous/results/results_images_20261125_194357.csv`.
