# IntensifierResearch

![Tests](https://github.com/WilliamMorales1/IntensifierResearch/actions/workflows/tests.yml/badge.svg)

Extracts intensifier + adjective/adverb tokens (*muy bueno*, *riquísimo*, *archiconocido*, *muy muy lejos*) from POS-tagged Spanish sociolinguistic interviews, classifies each adjective as predicative or attributive, and merges in speaker metadata. One row per adjective or adverb token, intensified or not (`--drop-invariant` keeps only hosts intensified at least once in the corpus), so the output is a variable envelope ready for variationist analysis. Results from an earlier version are published in [*Proceedings of the LSA* 11(1)](https://doi.org/10.3765/plsa.v11i1.6091).

Tagging, lemmas and the dependency parse come from [Stanza](https://stanfordnlp.github.io/stanza/). An earlier TagAnt pipeline was dropped; see [Why Stanza](#why-stanza).

```fish
conda env create -f environment.yml
conda activate intensifier-research
python pipeline/clean_transcripts.py   # data/original/*.docx -> data/text/*.txt
python pipeline/extract_stanza.py      # data/text -> output/intensifier_data_stanza_<date>.sqlite
```

Needs [Miniforge](https://github.com/conda-forge/miniforge) (conda), plus [LibreOffice](https://www.libreoffice.org/) for old `.doc` transcripts. The first Stanza run downloads the Spanish models (~130 MB).

## Inputs

| Path | Contents |
| --- | --- |
| `data/original/` | transcripts as `.docx`, one per speaker; the file name (without extension) is the `Speaker` id. Delete everything before the first line of dialogue. |
| `data/speaker_data_ALL_2026-3-12.xlsx` | one row per speaker: `Speaker` plus any metadata columns (`Gender`, `Age`, `Edu`, `Corpus`, ...), copied onto every token. Optional; pass another sheet with `--speakers`. |

## Pipeline

| Stage | File | What it does |
| --- | --- | --- |
| Clean | `clean_transcripts.py` | `.docx` to one turn per line. Drops parentheticals, labeled interviewer, relative and third-voice turns, then remaining speaker labels (`J: -pues`, `E.: ¿cómo?`). Also removes unlabeled interviewer speech: questions addressed to the participant (*usted*, *tú*, 2nd-person verbs), questions run together with them, and their lead-in. Keeps echoes (*¿mi casa?*), tag questions (*¿no le parece?*) and reported speech. |
| Tag (Stanza) | `extract_stanza.py` | Tags `data/text` into `data/stanza_tagged` (raw, never edited), applies `correct_tokens` into `data/stanza_corrected`, dependency-parses that into `data/stanza_parsed` (CoNLL-U). Every stage skips finished files, so an interrupted run resumes. |
| Extract | `extract.py` | Called by `extract_stanza.py`. Splits at sentence punctuation, finds each host and the intensifier right before it, normalizes lemmas (apocope, gender, number, *-ísimo*, *archi-*), applies the extraction rules, takes `Adj_type`, `Noun` and `Verb` from the parse, and writes SQLite (xlsx and csv with `--xlsx`, `--csv`). |

```fish
python pipeline/extract_stanza.py --workers 2            # fewer workers, ~1.8 GB RAM each
python pipeline/extract_stanza.py --drop-invariant       # only hosts intensified at least once
python pipeline/extract_stanza.py --xlsx --csv           # also write xlsx and csv next to the sqlite
```

Tagging and parsing all 314 transcripts takes about 2 hours each on a 4-core laptop; set `OMP_NUM_THREADS=1` or each worker spins 8 threads. After changing `correct_tokens`, delete `data/stanza_parsed/` so the parse reads the new tags.

## Output

`output/intensifier_data_stanza_<date>.sqlite` holds the full table. `--xlsx` and `--csv` write the same table as `.xlsx` and `.csv`.

| Column | Meaning |
| --- | --- |
| `Speaker` | transcript file name |
| `Phr_tagged`, `Phr` | the segment the token came from, tagged and plain |
| `Int` | intensifier (*muy*, *súper*, *-ísimo*, *re-*, *archi-*, ...) or `/` |
| `Double` | second intensifier (*muy muy*) or `/` |
| `Adj`, `Lex_Adj` | adjective host as written, and its masculine singular lemma |
| `Adv` | adverb host |
| `Adj_type` | `predicative`, `attributive` or `ambiguous` |
| `Noun` | noun the adjective modifies or describes |
| `Verb`, `Inf_Verb` | verb or copula tied to the host, as written and as its infinitive lemma |
| `Number` | token id within the speaker (`<Speaker>_01`, ...) |
| `Syllable` | syllables in the host |

`/` means not applicable or not found. The SQLite file is about half the size of the csv: speakers, phrases and short words are stored once, and the `intensifier_data` view rebuilds the table.

```python
import sqlite3
import pandas as pd

df = pd.read_sql("SELECT * FROM intensifier_data", sqlite3.connect("output/intensifier_data_stanza_YYYY-MM-DD.sqlite"))
```

`Adj_type`, `Noun` and `Verb` come from the parse: `amod` is attributive with the head noun; a `cop` child or an `xcomp` (*se puso feo*, *lo veo bonito*) is predicative with the subject (or object) as Noun; Verb is the first verb, copula or auxiliary up the head chain, for adverb rows too. Noun and Verb must appear in `Phr`, else `/`.

## Extraction rules

In `extract.py`:

| Case | Handling |
| --- | --- |
| fixed expressions: *bien hecho*, *mucho más/menos/mejor/peor/mayor/menor* | row dropped |
| non-gradable adverb hosts: *casi siempre/nunca*, *mucho también/ya/entonces/antes*, *mucho/bastante donde*, sentence adverbs | intensified row dropped, bare row kept |
| *más bien* + host | host kept, no intensifier |
| disfluency fragments (*muy bue muy bueno*, *muy d muy rápido*) | row dropped |
| feminine lemmas in *-dora/-tora/-sora* | *acogedora* -> *acogedor*, not *acogedoro* |
| *muchísimo/a/os*, *tantísimas* | row dropped |
| *-ísimo* bases (*grandísimo*, *facilísimo*, *cheverísimo*) | base form found in the corpus: *grande*, *fácil*, *chévere*, not *grando*, *facilo*, *chevero* |
| hosts never intensified anywhere in the corpus (*ya*, *entonces*, *mismo*, *último*), grouped by `Lex_Adj` or by the adverb with `--drop-invariant` (`analyze(..., drop_invariant=True)`), all their rows dropped; off by default |

Tagger corrections, `correct_tokens` in `extract_stanza.py` (each rule hand-checked on samples):

| Stanza error | Fix |
| --- | --- |
| turn-final words split (*casero* -> *caser* + *o*) | temporary period at the end of each turn |
| *muy poco* PRON | ADV after an intensifier |
| *es muy solo* ADV (= lonely) | ADJ, except after *mucho* (= only) |
| *San/Santa/Santo* ADJ | PROPN when capitalized |
| discourse *bueno/claro* ADJ (*bueno, ...*, *pero bueno eso*) | INTJ clause-initially or after a pause or conjunction, unless before a noun or after an intensifier |
| *mejor/peor* ADJ in adverb uses (*a lo mejor*, *mejor me voy*) | ADV, kept ADJ after a determiner, noun, copula or *lo* |
| *igual* ADJ = anyway (*pero igual se fue*) | ADV, kept ADJ before a noun or *a/de/en* |
| possessives *mío/tuyo/suyo/nuestro* ADJ | DET |
| *hay mucho venezolano* (noun as ADJ) | NOUN after DET *mucho* or *haber* |
| participle lemma = verb (*dado* -> *dar*), *chéveres* -> *chéver* | masculine singular form, *chévere* |
| nouns used as adjectives after *muy* (*muy amigo*, *muy niña*, *muy trabajadores*) NOUN | ADJ, except a short list (*muy falta de*, *muy toma trago*) |
| *chéere/chevre/chevere*, *conchudo* VERB or NOUN | ADJ |

Known gaps: *mucho* + adjective after a copula (*era mucho chusco*) is left alone as possibly dialectal; *solo* keeps Stanza's ADJ tags outside the quantifier rule; interviewer backchannels (*mhm*, *qué bueno*) on their own lines can't be told from the participant's.

## Why Stanza

Until 2026-11-01 a [TagAnt](https://www.laurenceanthony.net/software/tagant/) pipeline produced the same columns, with `Adj_type`, `Noun` and `Verb` from word order. It was dropped (last commit with it: `3fd93c8`) because:

- Stanza's errors are a closed list fixed by `correct_tokens`; TagAnt's are open-ended: dialectal and participial adjectives tagged NOUN or VERB (*maluco*, *berraco*, *chévere*, *amañado*), garbage lemmas (*deliciosa* -> *delició*), and Puerto Rican lateralized /r/ verbs tagged ADJ (*estal*, *hacel*), which biased that corpus's rate down.
- The dependency parse leaves 18.4% of adjective rows ambiguous, against 43.0% for word order.
- On the 652 tokens where the taggers disagreed on the host after an intensifier, hand judgment (before most `correct_tokens` rules) came out even, 311 TagAnt to 312 Stanza; the Stanza errors were since fixed by rule, TagAnt's were not fixable that way.

Snapshot, `2026-11-01`:

| | Stanza |
| --- | --- |
| rows | 119,002 |
| intensified rows | 9,339 |
| adjective rows | 51,401 |
| adjective rows intensified | 17.02% |
| `Adj_type` ambiguous | 18.4% |
| rows, `--drop-invariant` | 45,159 |
| adjective rows intensified, `--drop-invariant` | 23.11% |

## Tests

```fish
python -m pytest -q
ruff check . && ruff format --check .
```

One test file per pipeline module: lemma normalization, *-ísimo* and *archi-*, double intensifiers, negation, Adj_type from parsed sentences, every extraction rule and Stanza correction, speaker-label and interviewer removal, SQLite round trip, and an end-to-end run from corrected tags to xlsx and SQLite. CI runs both commands on every push to `main` and every pull request.

## Changes

October 2026. Spreadsheets made before this, including the data behind the *Proc. LSA* paper, used the old behavior.

- ADV-tagged intensifiers (*bastante*, *mucho*, *casi*) and *no* were also emitted as their own adverb tokens.
- Copula detection was a substring match, so *es* inside *desde* made the next adjective predicative. It now matches whole words or the *estar*/*ser*/*parecer* lemma.
- Noun detection checked for intensifiers by substring, so *re* inside *padre* made *padre rico* ambiguous instead of attributive.
- Speaker labels and interviewer, relative and third-voice turns were counted as participant speech; they are now removed.
- Added the extraction rules and the Stanza pipeline above.
- `--drop-invariant` drops hosts that are never intensified, since they show no variation. This removes most bare-adverb rows (*ya*, *más*, *entonces*).

November 2026: TagAnt support removed; Stanza is the only pipeline. `extract_tagant.py` became `extract.py`, and word-order `Adj_type`/`Verb`, TagAnt lemma repair and `compare_taggers.py` are gone.

## License

MIT
