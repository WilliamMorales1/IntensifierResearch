# Pipeline

## Inputs

| Path | Contents |
| --- | --- |
| `data/original/` | transcripts as `.docx`, one per speaker; the file name (without extension) is the `Speaker` id. Two formats are read as-is: PRESEEA (XML header with `codigo_hab`, `E:`/`I:` turns, markup like `<alargamiento/>`) and Cartagena (`A:`/`B:` turns, informant = whichever speaks more). `.doc` files need converting first (`convert_doc_docx`, LibreOffice). |
| `data/speaker_data_ALL_2026-3-12.xlsx` | one row per speaker: `Speaker` plus any metadata columns (`Gender`, `Age`, `Edu`, `Corpus`, ...), copied onto every token. Optional; pass another sheet with `--speakers`. |

## Stages

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

Dialect-specific corrections live in `pipeline/dialects/` (one file per dialect) and are off unless named with `--dialect`: `pr` for Puerto Rican lateralized /r/ (*cielto*, *celca*), `co` for Colombian *chévere* spellings, *entoes* and dropped d (*complicao*). The corpus needs both; see [`rules.md`](rules.md#dialect-corrections-pipelinedialects). The Colab job applies both before parsing.

After changing `correct_tokens`, delete `data/stanza_parsed/` so the parse reads the new tags. On a CPU, set `OMP_NUM_THREADS=1` or each worker spins 8 threads.

Every cleaning rule, tag correction and extraction rule, with token counts: [`rules.md`](rules.md).

## Running on Colab

The transformer tagger and parser take days on a laptop CPU and about 1 h 40 min on a free Colab T4 for all 310 transcripts (2026-11-01: tagging ~45 min, parsing ~25 min, plus restarts after a preempted VM). With the [`colab` CLI](https://github.com/googlecolab/google-colab-cli) set up:

```fish
scripts/colab/start.sh    # packs pipeline/, data/text and finished tags/parses, starts the job on a T4
tail -f data/colab/sync.log
cp -r data/colab/data/stanza_* data/    # once sync.log says DONE
python pipeline/extract_stanza.py --dialect pr --dialect co    # tags and parses nothing new, just extracts
```

Only files missing from `data/stanza_tagged` or `data/stanza_parsed` are processed, so to redo some transcripts delete their files from both. `sync.sh` (started by `start.sh`) pulls finished files back every 10 minutes and, since free VMs get preempted, starts a new VM from them after three failed pulls. It stops the VM when the job is done.
