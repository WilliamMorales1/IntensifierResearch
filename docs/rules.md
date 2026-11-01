# Rules

Every rule below was checked by hand on samples before it shipped. Counts are the tokens it changed on the 314-transcript corpus when it was added. Tests for each rule live in `tests/`.

## Transcript cleaning (`pipeline/clean_transcripts.py`)

Only text marked by a speaker label is removed. Unlabeled questions stay, even when they look addressed to the participant, since without audio they can't be told apart from the participant's own rhetorical questions.

| Case | Handling |
| --- | --- |
| docx turns | `A:` turns kept (`B:` for files starting `21`), other labeled turns dropped |
| parentheticals (*(risas)*), `•`, `·` | removed |
| one-line transcripts (LAPR, TUNJ) with turn labels | participant label = `I` if present, else the label used 20+ times; other labeled turns (interviewer, `X` third voice) dropped up to the next label, or through their question(s) when the participant answers on without a label (`E.: ... ¿cuántos años llevan juntos?, me decía ...`) |
| line-based transcripts (TCali, MEDE) | every labeled line is someone else (interviewer, relative, radio) and is dropped |
| *(tercera voz)* after the participant's label | dropped as a third voice |
| interviewer line labels `E.`, `E..`, `E:`, `e:`, `E ¿` | whole line dropped; lowercase `e ¿`, `e.` are the filler *eh* and stay |
| participant line labels `I.`, `i:`, `B.` | label dropped, words kept |
| remaining participant labels (`J: -pues`) | label dropped |
| first 350 words | dropped (`--skip-words`) |

## Stanza corrections (`correct_tokens` in `pipeline/extract_stanza.py`)

Raw tags in `data/stanza_tagged` are never edited; corrected ones go to `data/stanza_corrected`.

| Stanza error | Fix |
| --- | --- |
| turn-final words split: *casero* -> *caser* + *o* | temporary period at the end of each turn |
| *muy poco* PRON | ADV after an intensifier |
| *muy solo* ADV (= lonely) | ADJ, except after *mucho* (= only) |
| *San/Santa/Santo* ADJ | PROPN when capitalized |
| discourse *bueno/claro* ADJ | INTJ clause-initially before a pause or *que* |
| discourse *bueno/claro/exacto* in other slots (*pero bueno eso*, *. Bueno ahora*, *mjum exacto*, *claro claro*) | INTJ after punctuation, conjunction, interjection, filler, repeat or *sí/pues/porque/no/y/o/pero*, unless before a noun or after an intensifier |
| discourse *claro/bueno* after unaccented *si* or *entonces* (124) | INTJ |
| tag questions *¿cierto?*, *¿no cierto?*, *¿claro?* (561) | INTJ between *¿* and *?*; *es cierto?* kept |
| clause-final *claro/cierto* (*se lo comen claro*, *tú la conoces cierto ?*; 122) | INTJ unless after AUX, ADJ, DET, ADP, a predicative verb, *tener*, an intensifier, *-mente*, a color or *un* + noun |
| discourse *listo* (= OK: *y listo*; 120) | INTJ |
| laughter *jajaja*, discourse *bueno/claro* as ADV | INTJ |
| *mejor/peor* ADJ in adverb uses (*mejor dicho*, *a lo mejor*, *mejor me voy*) | ADV; kept ADJ after a determiner, noun, copula, predicative verb or *lo*. *dicho* after *mejor* -> VERB *decir* |
| *igual* ADJ = anyway (*pero igual se fue*) | ADV; kept ADJ before a noun or *a/de/en*, after DET, AUX, a predicative verb or an intensifier |
| possessives *mío/mía/tuyo/suyo/nuestro* ADJ | DET |
| *mucho* + noun as ADJ (*hay mucho venezolano*) | NOUN when *mucho* is DET or follows *haber* |
| *mucho* + nominalized ADJ outside a copula (*pasa mucho vicioso*; ~35) | masc. sg. -> NOUN unless after AUX, a copula, *poner/volver/seguir* or a repeated *mucho* |
| nouns used as adjectives after *muy* (*muy amigo*, *muy niña*; ~75) | ADJ when longer than 3 letters and not a real noun (*muy falta de*, *muy parte de*) |
| participle lemma = verb (*dado* -> *dar*) | masc. sg. form |
| *chéveres* -> *chéver*, *chevere*, *gritono* | *chévere*, *gritón* |
| dialect *chévere* (*chéere, chevre, chéer*), *conchudo* as VERB/NOUN/PROPN/ADV | ADJ |
| 1sg *vivo* (= I live) as ADJ (199) | VERB *vivir* unless after DET, AUX, a verb, an intensifier or *lo/tan/más/en*; 143 flipped |
| adverbial *primero* (*pues primero se prepara*; 151) | ADV unless after DET, ADP, AUX, NOUN, *lo* or a predicative verb, before NOUN/ADJ, or *primero y segundo* |
| compound nouns *medio ambiente*, *sala comedor*, *hora pico*, *ciclo vía*, *Estados Unidos*, *ave María* | NOUN/PROPN |
| *cuarto* (room, quarter hour) ADJ (103) | NOUN unless before a noun (*cuarto piso*) |
| *debido a* (61), *junto a/con* (34) | ADP, ADV |
| *total que*, *bueno total* (= anyway; 30) | ADV; *cambio total* kept |
| *seguro que* (= surely; 12) | ADV unless after AUX, DET, NOUN, a predicative verb or an intensifier |
| *medio día*, *media noche* (25), *ocho y media* (4) | NOUN, NUM |
| misspelled *echar* (*se le hecha*; 6) | VERB after a clitic |
| *puro/solo* + bare noun (*era puro barro*, *comiendo solo pescado*; 141) | *puro* DET, *solo* ADV; *aire puro*, *una sola casa* kept |
| Puerto Rican lateralized /r/ (*cielto*, *fuelte*, *impoltante*, *mejol*, *celca*, *estudial*, *polque*, *helmano*; ~80 types) | lemma l -> r; non-adjectives retagged VERB, SCONJ, NOUN, ADV |
| dropped intervocalic d (*complicao*, *pesao*, *consentio*, *tímia*) | lemma -ado, -ido |
| adverbial *mismo* (*ahí/ahora/aquí/así mismo*; 231) | ADV; *uno mismo*, *lo mismo* kept |
| lowercase *santo/santa* in names (*semana santa*, *espíritu santo*; 59) | PROPN; *todo el santo día* kept |
| mid-sentence capitalized ADJ (*Villa Nueva*), *nueva york* (36) | PROPN |
| enclitic imperatives as ADJ (*digámoslo*, *respétala*; ~40) | VERB |
| *tengo entendido* (25), *yo saludo* (16), *a menudo* (8) | VERB *entender*, VERB *saludar*, ADV |
| *-ísimo* adjectives as ADV (*contrato jugosísimo*) | ADJ unless an adverb base (*muchísimo*, *lejísimos*) |
| *-ona* lemmas as *-ono* or *-on* (*mamona* -> *mamon*, *cansonas*; ~20 types) | lemma *-ón* unless *mono*, *monótono*, *autóctono*, *-ciona* |
| vocative *hermano* ADJ | NOUN |
| *cerquita* ADJ, *por lo regular* | ADV |

## Extraction rules (`pipeline/extract.py`)

| Case | Handling |
| --- | --- |
| fixed expressions: *bien hecho*, *mucho más/menos/mejor/peor/mayor/menor* | row dropped |
| non-gradable adverb hosts: *casi siempre/nunca*, *mucho también/ya/entonces/antes/donde/anoche*, *bien primero*, sentence adverbs | intensified row dropped, bare row kept |
| function words as adverb hosts (*muy digamos*, *bien hasta con*, *mucho tanto*, *bien igual*, *casi toos*) | non-gradable, as above |
| *más bien* + host | host kept, no intensifier |
| disfluency fragments (*muy bue muy bueno*, *muy d muy rápido*, *muy comple es muy complejo*, *casi nun*) | row dropped |
| feminine lemmas in *-dora/-tora/-sora* | *acogedora* -> *acogedor* |
| singular *-s* and invariant *-a* lemmas (*gris*, *francés*, *egoísta*, *paisa*, *-ista*, *-crata*) | kept, not *gri*, *egoísto* |
| *muchísimo/a/os*, *tantísimas* | row dropped |
| *-ísimo* bases (*grandísimo*, *facilísimo*, *cheverísimo*) | base form found in the corpus: *grande*, *fácil*, *chévere*; adjective surface rebuilt (*grandas* -> *grandes*) |
| *-ísimo* on adverbs (*lejísimos*, *tardísimo*, *cerquísima*) | host *lejos*, *tarde*, *cerca*, Int `-ísimo`; *lejísimos* ADJ retagged ADV |
| *entoes*, *ahorita* as ADJ/NOUN/VERB/PRON | ADV |
| *poquito* | ADV after an intensifier or verb (*muy poquito*); DET before a noun and for *poquita/os/as*; NOUN (*un poquito*) kept |
| lateralized adverb hosts (*celca*, *talde*) | `Adv` uses the r lemma |
| hosts never intensified anywhere in the corpus (*ya*, *entonces*, *más*) | all rows dropped with `--drop-invariant`; off by default |

## Adj_type, Noun and Verb (`sentence_relations` in `pipeline/extract_stanza.py`)

| Parse | Adj_type | Noun |
| --- | --- | --- |
| `amod` | attributive | head, if NOUN/PROPN |
| `cop` child | predicative | nearest `nsubj` |
| `xcomp` (*se puso feo*, *lo veo bonito*) | predicative | head verb's `obj`, else `nsubj` |
| `obj/advcl/advmod/ccomp/parataxis` of *ser/estar/parecer/quedar/sentir* without a `case` child (*es como difícil*, *queda delicioso*) | predicative | as `cop` |
| `conj` or `amod` of an ADJ (*muy organizado muy bonito*) | inherits from the head | |
| `acl` of a NOUN without `cop` (*empresa llamada*) | attributive | head |
| head is a filler (*mhm*, *eeh*) or anything else | ambiguous | |

Verb is the first VERB, `cop` child or AUX up the head chain, for adverb rows too. Noun and Verb must appear in `Phr`, else `/`; an attributive row whose noun is outside `Phr` becomes ambiguous.

## Known gaps

- *mucho* + adjective after a copula (*era mucho chusco*) is left alone as possibly dialectal.
- Words split by the transcriber (*muy distin to*, *bastante agra dable*; ~15 tokens) keep the cut piece as host.
- Depictives parsed as `amod` (*tuvimos el hijo soltera*) and standalone comments attached to the nearest noun (*me da alegría, muy bueno*) get the wrong Adj_type.
- Unlabeled interviewer questions and backchannels (*mhm*, *qué bueno*) stay in the text.
