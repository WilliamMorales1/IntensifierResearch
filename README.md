# IntensifierResearch

![Tests](https://github.com/WilliamMorales1/IntensifierResearch/actions/workflows/tests.yml/badge.svg)

Extracts intensifier + adjective/adverb tokens (*muy bueno*, *riquísimo*, *archiconocido*, *muy muy lejos*) from POS-tagged Spanish sociolinguistic interviews. Each adjective is classified as predicative or attributive, and speaker metadata is merged in. Output is one row per adjective or adverb token, a variable envelope ready for variationist analysis.

Results from an earlier version are published in [*Proceedings of the LSA* 11(1)](https://doi.org/10.3765/plsa.v11i1.6091); that code is on the [`LSA-2026-paper`](../../tree/LSA-2026-paper) branch, with its citation.

## Quick start

```fish
conda env create -f environment.yml
conda activate intensifier-research
python pipeline/clean_transcripts.py                          # data/original/*.docx -> data/text/*.txt
python pipeline/extract_stanza.py --dialect pr --dialect co   # data/text -> output/intensifier_data_stanza_<date>.sqlite
```

Tagging and parsing use [Stanza](https://stanfordnlp.github.io/stanza/) transformer models (about 1 GB) and need a GPU; see [Running on Colab](docs/pipeline.md#running-on-colab). Extraction from finished parses runs on any laptop in about 5 minutes.

To try it without the corpus, `examples/` holds one synthetic interview:

```fish
python pipeline/clean_transcripts.py --input examples/original --output examples/text --skip-words 0
python pipeline/extract_stanza.py --input examples/text --tagged examples/stanza_tagged \
    --corrected examples/stanza_corrected --parsed examples/stanza_parsed \
    --speakers examples/speakers.xlsx --output examples/intensifier_data --csv
```

## Docs

- [Setup](docs/setup.md): conda, uv, pip, CPU-only PyTorch, tests.
- [Pipeline](docs/pipeline.md): inputs, stages, flags, dialects, Colab.
- [Output](docs/output.md): columns and reading the SQLite file.
- [Rules](docs/rules.md): every cleaning, correction and extraction rule.

## License

MIT
