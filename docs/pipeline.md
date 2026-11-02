# Pipeline

## Inputs

| Path | Contents |
| --- | --- |
| `data/original/` | transcripts as `.docx`, one per speaker; the file name (without extension) is the `Speaker` id. Two formats are read as-is: PRESEEA (XML header with `codigo_hab`, `E:`/`I:` turns, markup like `<alargamiento/>`) and Cartagena (`A:`/`B:` turns, informant = whichever speaks more). `.doc` files need converting first (`convert_doc_docx`, LibreOffice). |
| speaker sheet (`.xlsx`, any path) | one row per speaker: `Speaker` plus any metadata columns (`Gender`, `Age`, `Edu`, `Corpus`, ...), copied onto every token. Optional: pass it with `--speakers`; without it the output has no metadata columns. |

## Stages

| Stage | File | What it does |
| --- | --- | --- |
| Clean | `clean_transcripts.py` | `.docx` to one turn per line. Drops parentheticals, labeled interviewer, relative and third-voice turns, then remaining speaker labels (`J: -pues`, `E.: ¿cómo?`). Only labeled speech is removed; unlabeled questions stay, since they can't be told from the participant's own without audio. |
| Annotate (Stanza) | `annotate.py` | Tags `data/text` into `data/stanza_tagged` (raw, never edited), applies `correct_tokens` into `data/stanza_corrected`, dependency-parses that into `data/stanza_parsed` (CoNLL-U). Every stage skips finished files, so an interrupted run resumes. |
| Extract | `extract.py` | Splits at sentence punctuation, finds each host and the intensifier right before it, normalizes lemmas (apocope, gender, number, *-ísimo*, *archi-*), applies the extraction rules, takes `Adj_type`, `Noun` and `Verb` from the parse, and writes SQLite (xlsx and csv with `--xlsx`, `--csv`). |

`run.py` chains both stages and holds the CLI.

```fish
python pipeline/run.py --workers 2            # fewer workers, ~1.8 GB RAM each
python pipeline/run.py --drop-invariant       # only hosts intensified at least once
python pipeline/run.py --xlsx --csv           # also write xlsx and csv next to the sqlite
```

Dialect-specific corrections live in `pipeline/dialects/` (one file per dialect) and are off unless named with `--dialect`: `pr` for Puerto Rican lateralized /r/ (*cielto*, *celca*), `co` for Colombian *chévere* spellings, *entoes* and dropped d (*complicao*). The corpus needs both; see [`rules.md`](rules.md#dialect-corrections-pipelinedialects). The Colab job applies both before parsing.

After changing `correct_tokens`, the next run reparses only the files whose corrected tags no longer match their parse; a handful of files parse fine on a CPU (the demo interview takes about 45 s and 2.3 GB). Workers run single-threaded (`OMP_NUM_THREADS=1` unless set), and a worker that cannot load its models stops the run instead of restarting forever.

Every cleaning rule, tag correction and extraction rule, with token counts: [`rules.md`](rules.md).

## Running on Colab

The transformer tagger and parser take days on a laptop CPU and about 1 h 40 min on a free Colab T4 for all 310 transcripts (2026-11-01: tagging ~45 min, parsing ~25 min, plus restarts after a preempted VM). With the [`colab` CLI](https://github.com/googlecolab/google-colab-cli) set up:

```fish
scripts/colab/start.sh    # packs pipeline/, data/text and finished tags/parses, starts the job on a T4
tail -f data/colab/sync.log
cp -r data/colab/data/stanza_* data/    # once sync.log says DONE
python pipeline/run.py --dialect pr --dialect co    # tags and parses nothing new, just extracts
```

Only files missing from `data/stanza_tagged` or `data/stanza_parsed`, and parses outdated by a `correct_tokens` change, are processed, so to redo some transcripts delete their files from both. `sync.sh` (started by `start.sh`) pulls finished files back every 10 minutes and, since free VMs get preempted, starts a new VM from them after three failed pulls. It stops the VM when the job is done.
