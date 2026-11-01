# IntensifierResearch

![Tests](https://github.com/WilliamMorales1/IntensifierResearch/actions/workflows/tests.yml/badge.svg)

Extracts intensifier + adjective/adverb tokens (*muy bueno*, *riquísimo*, *archiconocido*, *muy muy lejos*) from POS-tagged Spanish sociolinguistic interviews, classifies each adjective as predicative or attributive, and merges in speaker metadata. One row per adjective or adverb token, intensified or not (`--drop-invariant` keeps only hosts intensified at least once in the corpus), so the output is a variable envelope ready for variationist analysis. Results from an earlier version are published in [*Proceedings of the LSA* 11(1)](https://doi.org/10.3765/plsa.v11i1.6091); that code is on the [`LSA-2026-paper`](../../tree/LSA-2026-paper) branch, with its citation.

Tagging, lemmas and the dependency parse come from [Stanza](https://stanfordnlp.github.io/stanza/). An earlier TagAnt pipeline was dropped; see [Why Stanza](#why-stanza).

```fish
conda env create -f environment.yml
conda activate intensifier-research
python pipeline/clean_transcripts.py   # data/original/*.docx -> data/text/*.txt
python pipeline/extract_stanza.py      # data/text -> output/intensifier_data_stanza_<date>.sqlite
```

Needs Python 3.10+ and [LibreOffice](https://www.libreoffice.org/) for old `.doc` transcripts. Tagging and parsing use Stanza's transformer models (BERTIN RoBERTa, about 1 GB of downloads) and need a GPU; see [Running on Colab](#running-on-colab). Extraction from finished tags and parses runs on any laptop in about 5 minutes.

To try the whole pipeline without the corpus, `examples/` holds one synthetic interview with its tags, parse and output:

```fish
python pipeline/clean_transcripts.py --input examples/original --output examples/text --skip-words 0
python pipeline/extract_stanza.py --input examples/text --tagged examples/stanza_tagged \
    --corrected examples/stanza_corrected --parsed examples/stanza_parsed \
    --speakers examples/speakers.xlsx --output examples/intensifier_data --csv
```

## Setup

Pick one. Nothing is installed as a package; the scripts run from the repo root.

**conda** ([Miniforge](https://github.com/conda-forge/miniforge)), what CI uses:

```fish
conda env create -f environment.yml
conda activate intensifier-research
```

**uv**: `uv sync` builds `.venv` from `uv.lock`, dev tools (pytest, ruff) included. Prefix commands with `uv run` or activate the env.

```fish
uv sync
uv run python -m pytest -q
uv run python pipeline/extract_stanza.py
```

**venv + pip** (pip 25.1+ for `--group`):

```fish
python -m venv .venv
source .venv/bin/activate.fish     # bash/zsh: source .venv/bin/activate
pip install . --group dev          # drop --group dev to skip pytest and ruff
```

Stanza pulls in PyTorch, whose default Linux wheel bundles CUDA (~3 GB). On a machine without an NVIDIA GPU, install the CPU wheel (~200 MB) first:

```fish
pip install torch --index-url https://download.pytorch.org/whl/cpu   # then: pip install . --group dev
# uv equivalent, skipping the lockfile:
uv venv
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -r pyproject.toml --group dev
```

After editing dependencies, update both `pyproject.toml` and `environment.yml`, then run `uv lock`.

## Inputs

| Path | Contents |
| --- | --- |
| `data/original/` | transcripts as `.docx`, one per speaker; the file name (without extension) is the `Speaker` id. Delete everything before the first line of dialogue. |
| `data/speaker_data_ALL_2026-3-12.xlsx` | one row per speaker: `Speaker` plus any metadata columns (`Gender`, `Age`, `Edu`, `Corpus`, ...), copied onto every token. Optional; pass another sheet with `--speakers`. |

## Pipeline

| Stage | File | What it does |
| --- | --- | --- |
| Clean | `clean_transcripts.py` | `.docx` to one turn per line. Drops parentheticals, labeled interviewer, relative and third-voice turns, then remaining speaker labels (`J: -pues`, `E.: ¿cómo?`). Only labeled speech is removed; unlabeled questions stay, since they can't be told from the participant's own without audio. |
| Tag (Stanza) | `extract_stanza.py` | Tags `data/text` into `data/stanza_tagged` (raw, never edited), applies `correct_tokens` into `data/stanza_corrected`, dependency-parses that into `data/stanza_parsed` (CoNLL-U). Every stage skips finished files, so an interrupted run resumes. |
| Extract | `extract.py` | Called by `extract_stanza.py`. Splits at sentence punctuation, finds each host and the intensifier right before it, normalizes lemmas (apocope, gender, number, *-ísimo*, *archi-*), applies the extraction rules, takes `Adj_type`, `Noun` and `Verb` from the parse, and writes SQLite (xlsx and csv with `--xlsx`, `--csv`). |

```fish
python pipeline/extract_stanza.py --workers 2            # fewer workers, ~1.8 GB RAM each
python pipeline/extract_stanza.py --drop-invariant       # only hosts intensified at least once
python pipeline/extract_stanza.py --xlsx --csv           # also write xlsx and csv next to the sqlite
```

After changing `correct_tokens`, delete `data/stanza_parsed/` so the parse reads the new tags. On a CPU, set `OMP_NUM_THREADS=1` or each worker spins 8 threads.

### Running on Colab

The transformer tagger and parser take days on a laptop CPU and about 1 h 40 min on a free Colab T4 for all 314 transcripts. With the [`colab` CLI](https://github.com/googlecolab/google-colab-cli) set up:

```fish
scripts/colab/start.sh    # packs pipeline/, data/text and finished tags/parses, starts the job on a T4
tail -f data/colab/sync.log
cp -r data/colab/data/stanza_* data/    # once sync.log says DONE
python pipeline/extract_stanza.py       # tags and parses nothing new, just extracts
```

Only files missing from `data/stanza_tagged` or `data/stanza_parsed` are processed, so to redo some transcripts delete their files from both. `sync.sh` (started by `start.sh`) pulls finished files back every 10 minutes and, since free VMs get preempted, starts a new VM from them after three failed pulls. It stops the VM when the job is done.

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

## Rules

[`docs/rules.md`](docs/rules.md) lists every transcript cleaning rule, Stanza tag correction (`correct_tokens`), extraction rule and the `Adj_type` mapping, with the number of tokens each one changed.

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

`examples/` doubles as an end-to-end check: rerunning the commands under the first section should reproduce `examples/intensifier_data.csv`.

One test file per pipeline module: lemma normalization, *-ísimo* and *archi-*, double intensifiers, negation, Adj_type from parsed sentences, every extraction rule and Stanza correction, speaker-label and interviewer removal, SQLite round trip, and an end-to-end run from corrected tags to xlsx and SQLite. CI runs both commands on every push and pull request.

## Changes

October 2026. Spreadsheets made before this, including the data behind the *Proc. LSA* paper, used the old behavior.

- ADV-tagged intensifiers (*bastante*, *mucho*, *casi*) and *no* were also emitted as their own adverb tokens.
- Copula detection was a substring match, so *es* inside *desde* made the next adjective predicative. It now matches whole words or the *estar*/*ser*/*parecer* lemma.
- Noun detection checked for intensifiers by substring, so *re* inside *padre* made *padre rico* ambiguous instead of attributive.
- Speaker labels and interviewer, relative and third-voice turns were counted as participant speech; they are now removed.
- Added the extraction rules and the Stanza pipeline above.
- `--drop-invariant` drops hosts that are never intensified, since they show no variation. This removes most bare-adverb rows (*ya*, *más*, *entonces*).

November 2026:

- TagAnt support removed; Stanza is the only pipeline. `extract_tagant.py` became `extract.py`, and word-order `Adj_type`/`Verb`, TagAnt lemma repair and `compare_taggers.py` are gone.
- Stanza moved to its transformer models (BERTIN RoBERTa pos and depparse), pinned to 1.15.0.
- Interviewer removal is label-only. Unlabeled questions that looked addressed to the participant used to be removed too; that guessed wrong too often.
- A capital *A* starting a sentence (*A mí me parece*, *A veces*) was deleted as a leftover speaker label; it is now kept.

## License

MIT
