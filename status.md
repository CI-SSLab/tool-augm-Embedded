# Stato del lavoro: estensione subacquea

Aggiornato al 23 novembre 2026.

## Da dove partiamo

Il fork `tool-augm-Embedded` è una copia esatta della repo del paper (stesso commit, `9a4a36f`). L'agente risponde a domande sugli artisti europei: estrae il nome con una regex, interroga Europeana con la cascata a tre stadi e cita i record che trova. L'estensione aggiunge le domande con foto per il patrimonio sommerso, senza cambiare il percorso testuale del paper.

## Ambiente

Lavoriamo su blackhole, perché il cluster del lab non è disponibile. La macchina ha una RTX 4060 da 8 GB e una GTX TITAN X da 12 GB.

EmbeddingGemma 2 gira sulla 4060 in bf16. Occupa 1,35 GB e codifica un'immagine in circa 0,2 secondi con il budget di default (280 token). L'API di sentence-transformers funziona come da documentazione.

L'account Ollama Cloud non ha crediti, quindi gpt-oss-20b gira in locale con Ollama. Il modello è diviso sulle due GPU (4,8 GB sulla 4060, 7,7 GB sulla TITAN X) e produce circa 38 token al secondo: un turno completo dell'agente richiede circa 25 secondi. Per farlo stare su entrambe le schede bisogna passare da Vulkan, perché la TITAN X con il driver installato non è supportata da CUDA in Ollama. I pesi sono gli stessi del cloud, ma la regressione del paper andrebbe comunque rilanciata nelle stesse condizioni di allora, se si recuperano i crediti.

## Cosa c'è nelle fonti

Abbiamo interrogato Europeana e il knowledge graph ArCo dell'ICCD per ogni candidato del gruppo curato. I JSON grezzi sono in `data/census/`.

Su Europeana il patrimonio sommerso in quanto tale quasi non c'è. Punta Epitaffio, Pavlopetri e le ricerche "underwater archaeology" sulla Grecia restituiscono zero record; "Baia" restituisce soprattutto baie geografiche e Baia Mare in Romania. I Bronzi di Riace compaiono in 86 record, ma 85 sono foto di eventi al Quirinale; il Satiro di Mazara ha lo stesso problema. Vanno molto meglio i bronzi greci: lo Zeus/Poseidon di Capo Artemisio ha 13 viste da museo, il Fantino 5, l'Efebo di Anticitera 9 (alcune in CC BY da SearchCulture.gr).

Le statue del Ninfeo di Punta Epitaffio sono su Europeana tramite l'archivio del DAI e Foto Marburg: Ulisse, il compagno con l'otre, Dioniso e Antonia Augusta. Hanno una sola foto ciascuna. Per Ulisse e il compagno la scheda indica Baia come luogo; per Dioniso e Antonia il luogo manca.

ArCo risponde dall'endpoint ufficiale (il mirror del CNR no). Ci sono 68 schede con contesto di giacitura subacqueo, tutte del progetto ARCHEOMAR (2004-2005), 35 delle quali in Campania. La scheda del Ninfeo di Punta Epitaffio c'è: giacimento subacqueo, età romana imperiale, primo scavo di Nino Lamboglia nel 1959, con una foto subacquea di uno scavo. Le altre schede dell'area di Baia invece hanno come immagine solo mappe e rilievi, che non servono a un indice visivo. Delle 71 immagini collegate alle schede subacquee, quelle che sono foto vere e non riguardano relitti sono una manciata.

Le statue del Ninfeo non hanno una scheda di catalogo, quindi l'opera viene da Europeana e il sito da ArCo, come previsto. I dati di localizzazione di ArCo sono sporchi: schede di palazzi in Toscana risultano "all'interno del Castello di Baia". Il collegamento fra un'opera e il suo sito va quindi fatto per identificativo, con una tabella compilata a mano, e non cercando il nome del luogo nei testi.

Quasi tutte le foto di Europeana sono "In Copyright". Possiamo usarle per costruire l'indice di ricerca, non per le slide o la demo pubblica. Per le foto ICCD la licenza non compare nei dati.

## Il gruppo curato, per ora

Il file `data/census/curated_group.csv` contiene 13 elementi: 8 reperti musealizzati (le quattro statue di Baia, Zeus/Poseidon e Fantino di Artemisio, Efebo e Filosofo di Anticitera) e 5 strutture in situ prese dalle schede ArCo che hanno una foto utilizzabile. Per ogni elemento ci sono gli ID dei record, il numero di viste, le licenze e la scheda del sito quando esiste. Un solo elemento è marcato come verificato; gli altri aspettano un controllo a mano.

## La baseline testuale sul gruppo

Prima di scrivere codice nuovo abbiamo fatto girare l'agente del paper, senza modifiche, su nove domande che riguardano il gruppo ("Parlami dello Zeus di Capo Artemisio", "Cos'è il Ninfeo di Punta Epitaffio?" e simili).

Non ha trovato nessun record pertinente. Sulle statue di Baia il tool ha cercato "Baia" e ha restituito monumenti di Baia Mare; nelle altre sette domande ha restituito zero risultati, e in un caso la query è arrivata vuota a Europeana, che ha risposto con un errore.

Le risposte sono il problema più serio. Il prompt chiede all'agente di rispondere comunque con la conoscenza generale quando il tool non trova nulla, e su questi oggetti la conoscenza generale di gpt-oss-20b non regge: ha scritto che "Baia" è uno scultore, che Capo Artemisio è un artista greco, che l'Efebo di Anticitera è uno scultore del V secolo, che Miseno è in provincia di Salerno e che Punta Epitaffio è vicino a Roma. Il tool è costruito attorno al nome di un artista (regex, filtro `who:`, controllo sul creatore) e qui non c'è nessun artista da estrarre.

Senza un modo diverso di identificare l'oggetto, il sistema produce le invenzioni che il paper voleva evitare, ed è il motivo principale per fare l'estensione. Le prove, con i risultati e i file, sono descritte in `journey.md`.

## Decisioni da prendere

1. I bronzi recuperati da relitti (Artemisio, Anticitera, e quelli di Punta del Serrone a Brindisi, che hanno una scheda ArCo con foto) entrano nel gruppo? Sono gli unici elementi con molte viste.
2. Dioniso e Antonia vengono davvero da Baia, e le quattro statue da Punta Epitaffio? Le schede non lo dicono in modo esplicito.
3. Va bene usare foto "In Copyright" solo per l'indice?
4. Con una sola vista per statua, il riconoscimento delle statue di Baia sarà fragile. Servono foto subacquee di buona qualità per le query, idealmente scattate dal team.

## Prossimi passi

Il prossimo pezzo è il modulo di embedding con l'indice: encoder intercambiabile (EmbeddingGemma 2, con SigLIP 2 come alternativa), matrice normalizzata salvata su disco, più viste per oggetto, costruzione incrementale. Poi il tool immagine, prima da riga di comando: similarità, aggregazione per oggetto, decisione con soglia e margine, lettura dei record per ID da Europeana e ArCo in una sola invocazione. Solo dopo l'integrazione nell'agente e nell'interfaccia Streamlit, dietro un flag spento di default.

Per la presentazione, dopo i test sulle immagini, servono grafici che mostrino come lavorano gli embedding: la matrice di similarità coseno fra gli oggetti del gruppo, la distribuzione dei punteggi fra viste dello stesso oggetto e fra oggetti diversi, alcune query con i primi k risultati in miniatura e il loro punteggio, e una proiezione 2D delle viste colorate per oggetto.

## Test previsti

Le query saranno sempre coppie foto più domanda, con quattro modelli di domanda: cos'è, a che epoca risale, da quale sito proviene, e una domanda con una premessa falsa (per esempio "È la statua trovata a Pompei?" su un oggetto di Baia). L'ultima serve a vedere se il modello o la pipeline prendono per buono quello che scrive l'utente: la risposta deve riportare il sito della scheda, o dire che il dato non c'è, senza confermare Pompei.

| Insieme | Contenuto | Scopo | Quante |
|---|---|---|---|
| C0 | foto da museo | limite superiore nello stesso dominio | circa 30 |
| C1 | foto subacquee | misura principale | 45-60 |
| C2 | negativi difficili (altri siti, statue non indicizzate, fondali vuoti) | capacità di rifiutare | 25-30 |
| Validazione | 15 subacquee e 10 negativi, disgiunte dal resto | tarare soglia e margine | circa 25 |
| Regressione | le 150 query e le 42 sessioni del paper | verificare che il percorso testuale non cambi | tutte |

Per le immagini misureremo top-1 e top-5 su C0 e C1, la differenza fra i due (quanto costa il passaggio dal museo al fondale), i rifiuti corretti su C2, i falsi rifiuti su C0 e C1, la curva rischio-copertura al variare della soglia e la latenza. Le varianti da confrontare sono l'encoder, il budget di token, la correzione colore (nessuna, gray-world, gray-world più CLAHE) e una vista contro tutte le viste.

Sulle risposte controlleremo a mano che nessun titolo, luogo, sito o URL compaia senza essere nelle schede recuperate, anche quando il riconoscimento sbaglia: è la stessa garanzia del paper, applicata alle foto. Le metriche del paper (disciplina del tool, aderenza alle fonti, copertura e violazioni temporali) si riportano con la stessa cautela del paper.

Gli elementi del gruppo sono pochi, quindi è uno studio pilota e va presentato così.

## Scadenze

Demo end-to-end e regressione entro il 28 novembre, freeze del codice il 3 dicembre, presentazione all'ELIZA Research Forum il 10-11 dicembre.
