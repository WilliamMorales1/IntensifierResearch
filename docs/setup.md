# Setup

Pick one. Nothing is installed as a package; the scripts run from the repo root. Needs Python 3.10+ and [LibreOffice](https://www.libreoffice.org/) for old `.doc` transcripts.

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

## CPU-only PyTorch

Stanza pulls in PyTorch, whose default Linux wheel bundles CUDA (~3 GB). On a machine without an NVIDIA GPU, install the CPU wheel (~200 MB) first:

```fish
pip install torch --index-url https://download.pytorch.org/whl/cpu   # then: pip install . --group dev
# uv equivalent, skipping the lockfile:
uv venv
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -r pyproject.toml --group dev
```

## Changing dependencies

After editing dependencies, update both `pyproject.toml` and `environment.yml`, then run `uv lock`.

## Tests

```fish
python -m pytest -q
ruff check . && ruff format --check .
```

`examples/` doubles as an end-to-end check: rerunning the example commands in the README should reproduce `examples/intensifier_data.csv`.

One test file per pipeline module: lemma normalization, *-ísimo* and *archi-*, double intensifiers, negation, Adj_type from parsed sentences, every extraction rule and Stanza correction, speaker-label and interviewer removal, SQLite round trip, and an end-to-end run from corrected tags to xlsx and SQLite. CI runs both commands on every push and pull request.
