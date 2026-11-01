#!/bin/bash
# pulls finished files from Colab into data/colab every 10 min so a lost VM keeps them; restarts after 3 failures
repo=$(cd "$(dirname "$0")/../.." && pwd)
session=${COLAB_SESSION:-intensifier}
cd "$repo/data/colab"
fails=0
while true; do
  echo 'import subprocess; print(subprocess.run("cd /content/proj && cp /content/job.log . ; tar czf /content/sync.tgz --exclude=*.part job.log data/stanza_tagged data/stanza_corrected data/stanza_parsed 2>/dev/null", shell=True, capture_output=True, text=True).stdout)' \
    | timeout 300 colab exec -s "$session" > last_exec.txt 2>&1
  if timeout 600 colab download -s "$session" /content/sync.tgz sync.tgz.new >> sync.log 2>&1 && tar tzf sync.tgz.new > /dev/null 2>&1; then
    mv sync.tgz.new sync.tgz && tar xzf sync.tgz
    fails=0
    echo "$(date +%T) tagged=$(ls data/stanza_tagged 2>/dev/null | wc -l) parsed=$(ls data/stanza_parsed 2>/dev/null | wc -l)" >> sync.log
  else
    fails=$((fails + 1))
    echo "$(date +%T) sync failed ($fails)" >> sync.log
    # VM gone (preempted or runtime cap): rebuild it from the synced files, unless every file already came back
    if [ $fails -ge 3 ] && [ "$(ls data/stanza_parsed 2>/dev/null | wc -l)" -ge "$(ls "$repo/data/text" | wc -l)" ]; then
      echo "$(date +%T) session lost after all files synced, done" >> sync.log
      break
    fi
    if [ $fails -ge 3 ] && ! colab sessions 2>&1 | grep -q "$session"; then
      echo "$(date +%T) session lost, restarting" >> sync.log
      exec "$repo/scripts/colab/start.sh" >> sync.log 2>&1
    fi
  fi
  # the status exec can time out, so DONE is read from the synced job.log
  grep -q DONE job.log 2>/dev/null && { echo "$(date +%T) job DONE" >> sync.log; colab stop -s "$session"; break; }
  sleep 600
done
