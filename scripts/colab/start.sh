#!/bin/bash
# packs pipeline/, data/text and the local tagged/parsed files, starts the Stanza job on a fresh Colab T4 and
# launches sync.sh; only files missing from data/stanza_tagged or data/stanza_parsed, or with an outdated parse, are tagged or parsed.
# Rerun after a lost VM: files already synced back are uploaded and skipped
set -e
repo=$(cd "$(dirname "$0")/../.." && pwd)
stage=$repo/data/colab
session=${COLAB_SESSION:-intensifier}
mkdir -p "$stage"
cd "$stage"
pkill -f "scripts/colab/sync\.sh" || true
# tagged/parsed files are copied in so finished ones are skipped; delete a file from both to redo it
tar czf job.tgz -C "$repo" --exclude='*.part' pipeline data/text $(cd "$repo" && ls -d data/stanza_tagged data/stanza_parsed 2>/dev/null)
colab stop -s "$session" 2>/dev/null || true
colab new -s "$session" --gpu T4
colab upload -s "$session" job.tgz /content/job.tgz
colab upload -s "$session" "$repo/scripts/colab/job.py" /content/job.py
[ -f sync.tgz ] && colab upload -s "$session" sync.tgz /content/sync.tgz
cat > setup_vm.py <<'PY'
import subprocess
cmd = """cd /content && mkdir -p proj && tar xzf job.tgz -C proj && { [ -f sync.tgz ] && tar xzf sync.tgz -C proj || true; }
pip install -q stanza==1.15.0
python -c 'import stanza; stanza.download("es", package="default_accurate", processors="tokenize,mwt,pos,lemma,depparse")'
python -c 'from huggingface_hub import snapshot_download as s; s("bertin-project/bertin-roberta-base-spanish")'
nohup python -u job.py > job.log 2>&1 &"""
print(subprocess.run(cmd, shell=True, capture_output=True, text=True, executable="/bin/bash").stdout[-500:])
PY
# the client may time out on the long pip/model setup while the VM keeps going
colab exec -s "$session" -f setup_vm.py || echo "setup exec ended early"
COLAB_SESSION=$session nohup "$repo/scripts/colab/sync.sh" > /dev/null 2>&1 &
echo started
