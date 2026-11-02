# Rules

Every rule below was checked by hand on samples before it shipped. Counts are the tokens it changed on the 314-transcript corpus when it was added. Tests for each rule live in `tests/`.

## Transcript cleaning (`pipeline/clean_transcripts.py`)

Only text marked by a speaker label is removed. Unlabeled questions stay, even when they look addressed to the participant, since without audio they can't be told apart from the participant's own rhetorical questions.

| Case | Handling |
| --- | --- |
| docx text | paragraphs plus table cells (Tunja generations 2-3 put the dialogue in a table); line-number cells skipped |
| compilation docx (several *Informante Nº* sections, e.g. `34-Informante`) | only the section whose number is the first number in the file name |
| Cartagena turns | `A:` or `B:` turns, whichever has more words (the informant; `B` only in `TrCTG_H21`), other labeled turns dropped |
| PRESEEA header (Medellín, Cali, Tunja) | everything through the last `codigo_hab` line dropped, plus the `E: Entrevistador` legend |
| PRESEEA turns | `I` turns kept; labels `E:`, `I.:`, `e:`, colon-less line-initial `E.`/`I.` (Tunja), mid-line `E:`; every other header code (`A1`, `B`, ...) dropped |
| PRESEEA unlabeled line after an interviewer question (`E: ¿...?` then a line with no label) | informant's answer with its label missing (~360 words) |
| PRESEEA markup (`<alargamiento/>`, `<énfasis>...</énfasis>`, `<tiempo .../>`), stray `<`, `>`, `====` | tags removed, enclosed words kept |
| PRESEEA pauses `/`, `//` | `,` and `.` |
| parentheticals (*(risas)*), `•`, `·` | removed |
| one-line transcripts (LAPR, TUNJ) with turn labels | participant label = `I` if present, else the label used 20+ times; other labeled turns (interviewer, `X` third voice) dropped up to the next label, or through their question(s) when the participant answers on without a label (`E.: ... ¿cuántos años llevan juntos?, me decía ...`) |
| line-based transcripts (TCali, MEDE) | every labeled line is someone else (interviewer, relative, radio) and is dropped |
| *(tercera voz)* after the participant's label | dropped as a third voice |
| interviewer line labels `E.`, `E..`, `E:`, `e:`, `E ¿` | whole line dropped; lowercase `e ¿`, `e.` are the filler *eh* and stay |
| participant line labels `I.`, `i:`, `B.` | label dropped, words kept |
| remaining participant labels (`J: -pues`) | label dropped |
| `MEDE_H21_3` docx holds all of `MEDE_H21_2` pasted inside it (8,734 words, its own header says 33:47 and 5,186 words) | cut by hand 2026-11-02 from `data/text`, `stanza_tagged`, `stanza_corrected` and `stanza_parsed` together (originals in `data/duplicates/MEDE_H21_3_pre_slice/`); 919 -> 223 rows. The docx is unchanged, so re-cleaning it brings the copy back. The one parse chunk spanning the cut lost its first 15 tokens; their orphaned dependents hang on the first orphan (*despué*) as root |
| first 1,120 informant words (~ minute 10; `--start-minute 5` drops 510 instead) | dropped (`--start-minute`, or an exact `--skip-words`), only in files cleaned this run. Minute 10 is where the PRESEEA subject-pronoun (10-20) and attenuation (10-40) guides start, since the opening is the most formal stretch (see [Interview start](#interview-start)); 1,120 = median informant words at the 10:00 stamp in the 190 time-stamped MEDE/TCali files (middle half 952-1,269). One word count for every file because Tunja and Cartagena have no stamps. LAPR (no docx, already cut at 350) cut 770 more by hand on 2026-11-01. Interviews shorter than the cut are left empty, no exemption (`MEDE_H01_1`, 23 min) |

### Interview start

The 1,120-word cut is minute 10 of the interview, converted to words from this corpus's own time stamps. Minute 10 is where the PRESEEA guides for subject pronouns and attenuation start; the others start at minute 5 or 0. The first 10 minutes are treated as the most formal stretch (Guerrero González et al. 2024), the observer's paradox of Labov (1972).

- Labov, W. (1972). *Sociolinguistic Patterns*. Philadelphia: University of Pennsylvania Press, p. 209 (observer's paradox).
- Guerrero González, S. & Manjón-Cabeza Cruz, A. (2022). *Guía PRESEEA de estudio de la expresión del sujeto pronominal*. Minutes 10-20. <https://preseea.uah.es/sites/default/files/2022-05/Gu%C3%ADa%20PRESEEA%20de%20estudio%20de%20la%20expresi%C3%B3n%20del%20sujeto%20pronominal_Guerrero%20y%20Manj%C3%B3n%20(2022).pdf>
- Cestero Mancera, A. M. & Rodríguez Alfano, L. (2021). *Guía PRESEEA de estudio de la atenuación*. Minutes 10-40. <https://preseea.uah.es/sites/default/files/2022-02/Gu%C3%ADa%20PRESEEA%20de%20estudio%20de%20la%20atenuaci%C3%B3n_Cestero%20y%20Rodr%C3%ADguez%20%282021%29.pdf>
- Cestero Mancera, A. M. (2022). *Guía PRESEEA de estudio de apéndices interrogativos de control de contacto*. Minutes 5-40: 5-15 formal, 15-30 middle, 30-40 informal register. <https://preseea.uah.es/sites/default/files/2022-02/Gu%C3%ADa%20PRESEEA%20de%20estudio%20de%20ap%C3%A9ndices%20interrogativos%20de%20control%20de%20contacto_Cestero%20(2022).pdf>
- Samper Padilla, J. A., Malaver Arguinzones, I. & Samper Hernández, M. (2021). *Guía PRESEEA de estudio de la /d/ intervocálica*. First, middle and last five minutes. <https://preseea.uah.es/sites/default/files/2022-02/Gu%C3%ADa%20PRESEEA%20de%20estudio%20de%20la%20d%20intervoc%C3%A1lica_Samper,%20Malaver%20y%20Samper%20(2021).pdf>
- Guerrero González, S., González Riffo, J., Espinoza Díaz, V., Ibarra Herrera, D. & Gajardo Moller, C. (2024). Evidencialidad de acervo común: patrones sociopragmáticos en el habla de Santiago de Chile. *Philologica Canariensia* 30, 275-296. Minutes 5-35; the first 10 minutes are assumed closest to formal register. <https://ojsspdc.ulpgc.es/ojs/index.php/PhilCan/article/download/1662/1819?inline=1>

Word equivalent: informant words before the interpolated `<tiempo>` stamp, 190 MEDE and TCali files: 10:00 median 1,122 (middle half 952-1,269), used as 1,120; 5:00 median 512 (middle half 437-594), used as 510 by `--start-minute 5` (start of the interrogative-tag and evidentiality windows); 15:00 = 1,724. LAPR has no docx: for minute 5, cut 160 words from `data/text_pre_reclean/LAPR_*` (already cut at 350), not from `data/text`.

## Stanza corrections (`correct_tokens` in `pipeline/annotate.py`)

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
| *mucho, bien, casi, bastante, demasiado, harto*, *-mente* intensifiers the parse hangs on a verb, not on the host (*se cansara mucho acostada*, *comiendo mucho afuera*, *ver bien tranquilamente*, *habla mucho aquí*) | host kept, no intensifier (`verbal_int` in `sentence_relations`), unless the host is an ADJ under *ser/estar/parecer/quedar/sentir* (*quede bien limpiecita*). *muy, tan, súper* never grade verbs and are left alone. 12 intensified rows changed and 101 bare adverb rows added (they were dropped as intensified non-gradable before). Hand check of the 12: 9 right, 2 unclear (*iba bien amarrada*), 1 wrong (*vive bien mal*) |
| *mucho* + ADJ after a lexical verb (*compartimos mucho juntos*, *disfrutaran mucho necesario*) or + participle after *estar* (*he estado mucho hospitalizada*, = often) | host kept, no intensifier: *mucho* grades the verb or counts how often. 3 rows. *era mucho chusco*, *mucho mucho raro era* (dialectal *mucho* = *muy*) stay intensified |
| words split by the transcriber (*muy distin to*, *tan lejo s*, *muy calma do*, *bien cuida do*, *muy bue no*, *horri bles*, *entonce s*, *má s*, *actual mente*) | rejoined before extraction (`split_words`, `join_splits` in `analyze`; the second piece's parse entry is dropped, so no retag). *bue no* only after an intensifier (*son bue no son buenos* is a restart); *mucho cuida do* stays NOUN. 8 rows changed (5 intensified: *distinto* x2, *lejos* x2, *calmado*, *bueno*, *cuidado*; junk hosts *distin*, *lejo*, *calmo*, *ble* gone), 8 bare rows added (*entonces* x5, *horrible*, *calmado*, *actualmente*) |
| disfluency fragments (*muy bue muy bueno*, *muy d muy rápido*, *muy comple es muy complejo*, *casi nun*) | row dropped |
| feminine lemmas in *-dora/-tora/-sora* | *acogedora* -> *acogedor* |
| singular *-s* and invariant *-a* lemmas (*gris*, *francés*, *egoísta*, *paisa*, *-ista*, *-crata*) | kept, not *gri*, *egoísto* |
| *muchísimo/a/os*, *tantísimas* | row dropped |
| *-ísimo* bases (*grandísimo*, *facilísimo*, *cheverísimo*) | base form found in the corpus: *grande*, *fácil*, *chévere*; adjective surface rebuilt (*grandas* -> *grandes*) |
| *-ísimo* on adverbs (*lejísimos*, *tardísimo*, *cerquísima*) | host *lejos*, *tarde*, *cerca*, Int `-ísimo`; *lejísimos* ADJ retagged ADV |
| *ahorita* as ADJ/NOUN/VERB/PRON | ADV |
| *poquito* | ADV after an intensifier or verb (*muy poquito*); DET before a noun and for *poquita/os/as*; NOUN (*un poquito*) kept |
| lateralized adverb hosts (*celca*, *talde*) | `Adv` uses the r lemma `pr` gave it |
| hosts never intensified anywhere in the corpus (*ya*, *entonces*) | all rows dropped with `--drop-invariant`; off by default |

### Intensifier types and the envelope of variation

`Int_type` follows the scalar taxonomy of Quirk et al. (1985:589-590) as operationalized by Stratton & Sundquist (2022:388-389) and Stratton (2020): amplifiers are **maximizers** (upper extreme of the scale) or **boosters** (high point on the scale); downtoners are **approximators**, **compromisers**, **diminishers** or **minimizers**. **Emphasizers** are not scalar and "did not count as an instance of intensification" (Stratton & Sundquist 2022:395); their rows keep `Int` but should be counted as unintensified.

| Int_type | Int |
| --- | --- |
| maximizer | *absolutamente, completamente, totalmente, plenamente, extremadamente, sumamente* |
| booster | *muy, bien, mucho, harto, bastante, demasiado, súper, re-, archi-, -ísimo, realmente, verdaderamente, increíblemente, tan*, exclamative *más* |
| approximator | *casi* |
| compromiser | *más o menos* (Quirk's *more or less*; Norwegian *mer eller mindre* is a downtoner in Stratton & Sundquist 2022:391) |
| emphasizer | *especialmente, estrictamente* (like Norwegian *særlig* 'particularly') |

Following Stratton & Sundquist (2022:395), who follow Ito & Tagliamonte (2003) and D'Arcy (2015:459), comparative and superlative tokens, *as...as* comparisons, adjectives after 'how' and fossilized collocations are outside the envelope of variation, so their rows are dropped. Negative contexts, which they also drop, are kept and marked in `Negation` instead. *So* + adjective + *that* result clauses are dropped too, after Bulgin et al. (2008:103), since *so* there marks a result, not intensification (*that movie was so boring that I fell asleep*). Brown & Cortés-Torres (2013) and Orozco, Morales & Valenzuela (2026) left *tan* out entirely; here only its non-intensifying uses go. `degree_types` labels each *tan/más/menos* before a host on the whole file, so a result clause past a comma (*tan descarado , que*) is still seen. Counts are tokens on the 310-transcript corpus (2026-11-01).

| Case | Handling |
| --- | --- |
| *tan* + host (*es tan sencilla*, *¡ay tan guapa!*, *qué muchacho tan simpático*, *el dolor tan grande que uno tiene*: relative *que* is PRON; 692) | Int *tan*, booster (Stratton & Sundquist's *så syk* 'so sick') |
| *tan* X *como* (equality: *no es tan grande como este*, *tan bueno , como lo era*; 67) | row dropped; *como que* is a filler and stays |
| *tan* X *que* (result: *son tan atrevidos que*, *tan descarado , que hasta*; *tan* X *como para*; 62) | row dropped when the next word after any punctuation is SCONJ *que*; kept after exclamative *qué* (*¡qué profesor tan malo! , que ...*). Hand check of 40: ~33 real result clauses, the rest exclamatives or comparatives |
| *qué/cuán tan* X (= how: *no sé qué tan buenos*; 13) | row dropped, like Norwegian *hvor gammel*; clause-initial *¡ay, qué tan lindo!* is exclamative and kept |
| *tan solo/sólo/pronto/siquiera* (14) | row dropped |
| negation (*no es tan bueno*, *no muy bueno*, *no me parece muy bonito*, *nunca fue muy*, *ni tan pobres*, *no una casa tan grande*) | row kept, negator in `Negation`. Stratton & Sundquist (2022:395) drop negative contexts because negation "alters the semantic-pragmatic thrust of intensification"; marking them lets an analysis do the same or model them. From the parse: a *no/nunca/jamás/tampoco/ni* before the host hanging on the host, its intensifier, or a head up the chain through the first verb or predicate, and visible in `Phr`; without a parse, any earlier negator in the segment. The negator must also sit in a preverbal slot: the next word, past clitics, is on that chain, its copula, auxiliary, adverb, determiner or preposition, a verb whose infinitive is on the chain (*no se tenga que desplazar tan lejos*), or *tan* fixed to *ni*. That drops discourse *no* (*no , muy buena*, *no la gente de Cali es muy buena*, *no que era muy raro*, *no pues súper distinta*; 2026-11-02, 416 rows changed, 55 intensified; hand check of 30: 28 right, misses *tampoco a la gente le gusta muy hostigante*). 3,891 rows (454 intensified: *no* 396, *ni* 36, *tampoco* 12, *nunca* 10). Hand check of 28 kept negated intensified rows: 26 right; misses *ahora no aquí estoy muy amañado*, *no sé muy poquito* |
| *más/menos* X (*más grande*, *más caro que*, *mucho más*, *un poco más*, *menos favorecidas*; 2,290) | comparative, row dropped |
| *el/lo/mi* (N) *más/menos* X (*lo más importante*, *el momento más feliz*; 566) | superlative, row dropped |
| exclamative *¡qué* N *más* X*!* (*¡qué casa más bonita!*) | Int *más*, booster; 0 in the corpus |
| *más o menos* X (*más o menos bueno*; 48, 29 rows after other rules) | Int *más o menos*, compromiser |
| *por/a lo menos* X (= at least; 35) | host kept, Int `/` |
| *mejor, peor* hosts (ADJ or ADV) | comparative, row dropped |
| *mayor, menor* hosts | dropped unless intensified (*muy mayor* = elderly is a positive degree) |
| *tan, más, menos* as hosts themselves (9,631 rows, mostly bare *más*, *nada más*, cut-off *tan , tan*) | not hosts, like *muy* |

- Brown, E. L. & Cortés-Torres, M. (2013). Puerto Rican intensifiers: *Bien/muy* variables. In A. M. Carvalho & S. Beaudrie (eds.), *Selected Proceedings of the 6th Workshop on Spanish Sociolinguistics*, 11-19. Somerville, MA: Cascadilla Proceedings Project.
- Bulgin, J., Elford, N., Harding, L., Henley, B., Power, S. & Walters, C. (2008). So very really variable: Social patterning of intensifier use by Newfoundlanders online. *Linguistica Atlantica* 29, 101-115.
- D'Arcy, A. (2015). Stability, stasis and change. *Diachronica* 32, 449-493.
- Ito, R. & Tagliamonte, S. A. (2003). *Well* weird, *right* dodgy, *very* strange, *really* cool: Layering and recycling in English intensifiers. *Language in Society* 32(2), 257-279.
- Orozco, R., Morales, W. & Valenzuela, L. (2026). A variationist study of Spanish intensifiers. *Proceedings of the Linguistic Society of America*.
- Quirk, R., Greenbaum, S., Leech, G. & Svartvik, J. (1985). *A Comprehensive Grammar of the English Language*. London: Longman, pp. 589-590.
- Stratton, J. M. (2020). Adjective intensifiers in German. *Journal of Germanic Linguistics* 32(2), 183-215.
- Stratton, J. M. & Sundquist, J. D. (2022). A variationist sociolinguistic analysis of intensifiers in Oslo Norwegian. *Journal of Germanic Linguistics* 34(4), 385-419.

## Dialect corrections (`pipeline/dialects/`)

Off by default; `--dialect pr --dialect co` turns them on, and the corpus needs both. Each runs inside `correct_tokens` before the general rules (a dialect fix wins), and its lemma fixes run after them. Counts are tokens changed on the corpus.

| Dialect | Error | Fix |
| --- | --- | --- |
| `pr` (Puerto Rico, LAPR) | lateralized /r/ (*cielto*, *fuelte*, *impoltante*, *mejol*, *celca*, *estudial*, *polque*, *helmano*; ~80 types) | lemma l -> r; non-adjectives retagged VERB, SCONJ, NOUN, ADV |
| `co` (Colombia) | dialect *chévere* (*chéere, chevre, chéer*), *conchudo* as VERB/NOUN/PROPN/ADV | ADJ |
| `co` | dropped intervocalic d (*complicao*, *pesao*, *consentio*, *tímia*; mostly TUNJ) | lemma -ado, -ido |
| `co` | *entoes* (= *entonces*) as NOUN/VERB/ADJ/PART (291, nearly all TUNJ) | ADV |

Without them, those tokens keep Stanza's tag or lemma and the table has 100,260 rows (16.45% of adjective rows intensified) instead of 100,440 (16.46%) (2026-11-01, 310 transcripts, before the [envelope rules](#intensifier-types-and-the-envelope-of-variation)).

## Adj_type, Noun and Verb (`sentence_relations` in `pipeline/annotate.py`)

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

- Depictives parsed as `amod` (*tuvimos el hijo soltera*) and standalone comments attached to the nearest noun (*me da alegría, muy bueno*) get the wrong Adj_type.
- Unlabeled interviewer questions and backchannels (*mhm*, *qué bueno*) stay in the text.
