
## 25 novembre: primo test con foto subacquee vere

Il set di test subacqueo è costruito da Wikimedia Commons (`data/eval/underwater_queries.csv`, solo url e licenze, quasi tutte CC0 o CC BY-SA). Ogni categoria di Commons è assegnata a mano a una condizione; nelle categorie miste l'oggetto si ricava dal nome del file ("statua Dioniso", "statua Ulisse", "Antonia Minore"). Le etichette sono provvisorie e vanno controllate a mano: le foto numerate del museo di Baia e quelle del Parco senza nome (24) restano da etichettare e sono escluse dal conteggio.

| Condizione | Contenuto | Foto valutate |
|---|---|---|
| C0 | bronzi di Artemisio e di Anticitera fotografati al museo | 81 |
| C1 | copie delle statue sott'acqua a Punta Epitaffio, mosaici e pavimenti del Ninfeo | 20 (17 test, 3 validazione) |
| C2 | Portus Julius, vasi e iscrizioni del museo di Baia, bronzi di Riace, Satiro di Mazara, Cristo degli Abissi, Pavlopetri, Grado, Olous | 113 |

Per le statue di Baia non ci sono foto da museo con il nome nel file, quindi C0 contiene solo i bronzi greci. C1 è piccolo: su Commons ci sono solo 20 foto subacquee del Ninfeo.

| Correzione colore | C0 top-1 | C0 top-5 | C1 top-1 | C1 top-5 | C2 rifiutati (τ 0,80) |
|---|---|---|---|---|---|
| nessuna | 88,9% | 96,3% | 0% | 55% | 74 / 113 |
| gray-world | 88,9% | 93,8% | 0% | 55% | 74 / 113 |
| gray-world + CLAHE | 88,9% | 93,8% | 0% | 60% | 72 / 113 |

Nelle foto da museo l'oggetto viene riconosciuto, nelle foto subacquee mai. Il motivo si vede guardando dove finiscono: tutte le foto delle copie delle statue (Dioniso, Ulisse, Antonia) finiscono sulla scheda ICCD di Punta Epitaffio, la cui foto è anch'essa subacquea; le foto di mosaici e pavimenti finiscono sul porto sommerso di Mondragone. L'embedding riconosce prima di tutto "foto sott'acqua" e solo dopo l'oggetto. A livello di sito il risultato è diverso: per le statue il sito agganciato è quello giusto, e il top-1 sul sito sale al 60% (il collegamento statue → Punta Epitaffio però è ancora da verificare). La correzione colore non cambia quasi nulla: il salto di dominio non è solo una questione di colore.

Anche il rifiuto è debole: con τ = 0,80 un terzo dei negativi viene accettato, soprattutto come Dio di Artemisio (66 negativi su 113 lo hanno come primo risultato: è un "hub" che somiglia a qualunque statua di bronzo). Il validation set (3 foto C1 e 29 negativi) è troppo piccolo per tarare τ e δ in modo affidabile.

Le figure per la presentazione sono in `eval/underwater/results/figures/` (`eval/underwater/figures.py`): similarità fra gli oggetti, coseni stesso oggetto contro oggetti diversi, esempi di ricerca con i primi cinque risultati, proiezione PCA, curva rischio-copertura e top-1 per condizione. Le miniature dell'indice compaiono solo se la licenza è aperta. Nella PCA si vede lo stesso effetto: le foto C1 stanno vicino alle strutture in situ, lontano dalle statue da museo.
