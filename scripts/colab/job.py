# runs on the Colab VM: tags, corrects and parses data/text; finished files from an earlier VM are skipped
import os
import sys
import time

os.chdir("/content/proj")
sys.path.insert(0, "pipeline")
os.environ["HF_HUB_OFFLINE"] = "1"
import dialects
import extract_stanza as es

if __name__ == "__main__":
    t = time.time()
    es.tag_folder("data/text", "data/stanza_tagged", 1)
    print("TAGGED", time.time() - t, flush=True)
    # the parse reads the corrected tags, so it needs every dialect the corpus has
    es.correct_folder("data/stanza_tagged", "data/stanza_corrected", dialects.load(["pr", "co"]))
    es.parse_folder("data/stanza_corrected", "data/stanza_parsed", 1)
    print("PARSED", time.time() - t, flush=True)
    print("DONE", flush=True)
