# IntensifierResearch

![Tests](https://github.com/WilliamMorales1/IntensifierResearch/actions/workflows/tests.yml/badge.svg)

Extracts intensifier + adjective/adverb tokens (*muy bueno*, *riquísimo*, *archiconocido*, *muy muy lejos*) from POS-tagged Spanish sociolinguistic interviews. Each adjective is classified as predicative or attributive, and speaker metadata is merged in. Output is one row per adjective or adverb token, a variable envelope ready for variationist analysis.

Results from an earlier version are published in [*Proceedings of the LSA* 11(1)](https://doi.org/10.3765/plsa.v11i1.6091); that code is on the [`LSA-2026-paper`](../../tree/LSA-2026-paper) branch, with its citation.

## Dependencies

Python 3.10+ with [Stanza](https://stanfordnlp.github.io/stanza/) 1.15.0, PyTorch 2.6+, pandas, openpyxl (speaker sheets) and python-docx (transcripts). Dev: pytest, ruff. Pinned in `environment.yml` (conda) and `pyproject.toml` (uv/pip); see [Setup](docs/setup.md).

## Quick start

```fish
conda env create -f environment.yml
conda activate intensifier-research
python pipeline/clean_transcripts.py                          # data/original/*.docx -> data/text/*.txt, from minute 10 (--start-minute 5 for minute 5)
python pipeline/run.py --dialect pr --dialect co --speakers <sheet>.xlsx   # data/text -> output/intensifier_data_stanza_<date>.sqlite
```

Tagging and parsing use [Stanza](https://stanfordnlp.github.io/stanza/) transformer models (about 1 GB) and need a GPU; see [Running on Colab](docs/pipeline.md#running-on-colab). Extraction from finished parses runs on any laptop in about 5 minutes.

To try it without the corpus, `examples/` holds one synthetic interview:

```fish
python pipeline/clean_transcripts.py --input examples/original --output examples/text --skip-words 0
python pipeline/run.py --input examples/text --tagged examples/stanza_tagged \
    --corrected examples/stanza_corrected --parsed examples/stanza_parsed \
    --speakers examples/speakers.xlsx --output examples/intensifier_data --csv
```

## Intensifier classification

`Int_type` sorts intensifiers into maximizers, boosters, approximators, compromisers and emphasizers. This follows Quirk et al.'s (1985:589-590) scale as operationalized by Stratton & Sundquist (2022) and Stratton (2020). `Negation` records the negator (*no*, *nunca*, *ni*, *tampoco*, *jamás*) that scopes over a host. Negated rows are kept and marked, not dropped as in Stratton & Sundquist (2022:395).

The classification is partly arbitrary. The scale was written for English, and the class boundaries are judgment calls, not facts about Spanish:

- Stratton & Sundquist leave Norwegian *ganske* 'quite' out of their amplifier/downtoner counts because it does both jobs (2022:400, fn. 10), and *utrolig* 'unbelievably' because it is unclear whether it is an emphasizer, booster or maximizer (2022:396). Spanish has the same kind of items, but this pipeline gives each one a single class.
- *bastante* and *demasiado* are boosters because in this Colombian corpus they mostly mean 'very'. Elsewhere they can read as 'fairly' (compromiser) or 'too' (excess).
- *extremadamente* and *sumamente* are maximizers because Quirk lists *extremely* among them. Many studies call them boosters.
- *realmente*, *verdaderamente* and *increíblemente* are boosters, as *really* is in Tagliamonte's work. Quirk calls *really* an emphasizer.
- *-ísimo* and *archi-* are boosters, though grammars call *-ísimo* the *superlativo absoluto*.
- *más o menos* is a compromiser, after Quirk's *more or less*.
- Which uses of *tan* and *más* count as intensifiers is a rule-based guess: comparatives, *tan X como*, *tan X que* result clauses and 'how' readings are dropped. Earlier Spanish work dropped *tan* and *más* entirely (Brown & Cortés-Torres 2013; Orozco, Morales & Valenzuela 2026).

Check every class against your own reading before using `Int_type` in a model. The full mapping is one dictionary, `int_types` in `pipeline/extract.py`, and the rules and references are in [docs/rules.md](docs/rules.md#intensifier-types-and-the-envelope-of-variation).

## Docs

- [Setup](docs/setup.md): conda, uv, pip, CPU-only PyTorch, tests.
- [Pipeline](docs/pipeline.md): inputs, stages, flags, dialects, Colab.
- [Output](docs/output.md): columns and reading the SQLite file.
- [Rules](docs/rules.md): every cleaning, correction and extraction rule.

## License

MIT
