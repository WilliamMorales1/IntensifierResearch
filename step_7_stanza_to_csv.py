# tags the raw transcripts with stanza instead of TagAnt, then runs the same extraction as step 7

import argparse
import os
from datetime import date
from multiprocessing import Pool

import pandas as pd

from step_7_tagged_to_csv import (
    analyze,
    closest_verb_infinitive,
    closest_verb_non_infinitive,
    count_syllables,
    merge_speaker_data,
    numero,
    to_sqlite,
)

# the charlm pos model is ~25x slower on CPU, and the extraction never reads a parse
processors = {
    "tokenize": "combined_nocharlm",
    "mwt": "combined",
    "pos": "combined_nocharlm",
    "lemma": "combined_nocharlm",
}
speaker_data = "speaker_data_ALL_2026-3-12.xlsx"

_nlp = None


def clean_field(text):
    # spaces and underscores would break the word_POS_lemma format step 7 parses
    return (text or "").replace(" ", "").replace("_", "-")


def tag_word(word):
    return f"{clean_field(word.text)}_{word.upos}_{clean_field(word.lemma)}"


def tag_doc(doc, skip_chars=()):
    return "\n".join(
        " ".join(
            tag_word(w) for t in s.tokens if t.start_char not in skip_chars for w in t.words
        )
        for s in doc.sentences
    )


def join_paragraphs(paragraphs):
    # without final punctuation the tokenizer splits turn-final words (casero -> caser + o),
    # so a period is added and its offset returned for tag_doc to drop
    parts, added, pos = [], set(), 0
    for p in paragraphs:
        if p[-1] not in ".,;:!?¡¿…)]\"'":
            added.add(pos + len(p) + 1)
            p += " ."
        parts.append(p)
        pos += len(p) + 2
    return "\n\n".join(parts), added


def _init_worker():
    global _nlp
    import stanza
    import torch

    # one thread per process; extra threads per process made pos 25x slower here
    torch.set_num_threads(1)
    _nlp = stanza.Pipeline(
        "es", package=None, processors=processors, download_method=None, verbose=False
    )


def _tag_file(paths):
    src, dst = paths
    with open(src, encoding="utf-8") as f:
        paragraphs = [line.strip() for line in f if line.strip()]
    # blank-line paragraphs keep the tokenizer's input short, which is 10x faster than one blob
    text, added = join_paragraphs(paragraphs)
    doc = _nlp(text)  # type: ignore
    with open(dst + ".part", "w", encoding="utf-8") as f:
        f.write(tag_doc(doc, added) + "\n")
    os.replace(dst + ".part", dst)
    return os.path.basename(src)


def tag_folder(input_folder, output_folder, workers):
    import stanza

    stanza.download("es", package=None, processors=processors, verbose=False)
    os.makedirs(output_folder, exist_ok=True)
    for name in os.listdir(output_folder):
        if name.endswith(".part"):
            os.remove(os.path.join(output_folder, name))

    # already tagged files are reused so an interrupted run picks up where it stopped
    jobs = [
        (os.path.join(input_folder, name), os.path.join(output_folder, name))
        for name in sorted(os.listdir(input_folder))
        if name.endswith(".txt") and not os.path.exists(os.path.join(output_folder, name))
    ]
    print(f"Tagging {len(jobs)} files with stanza ({workers} workers)")
    with Pool(workers, initializer=_init_worker) as pool:
        for i, name in enumerate(pool.imap_unordered(_tag_file, jobs), 1):
            print(f"[{i}/{len(jobs)}] Tagged: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="text", help="folder of raw .txt transcripts")
    parser.add_argument("--tagged", default="stanza_tagged", help="where stanza output goes")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    tag_folder(args.input, args.tagged, args.workers)

    output = "intensifier_data_stanza_" + date.today().isoformat() + ".csv"
    df = analyze(args.tagged, output)

    df["Verb"] = df.apply(closest_verb_non_infinitive, axis=1)
    df["Inf_Verb"] = df.apply(closest_verb_infinitive, axis=1)
    number_counts = {}
    df["Number"] = df.apply(numero, axis=1, count_dict=number_counts)
    df["Syllable"] = df["Adj"].apply(count_syllables)
    if os.path.exists(speaker_data):
        df = merge_speaker_data(pd.read_excel(speaker_data), df)
    else:
        print(f"No {speaker_data}, skipping speaker metadata")

    for col in df.select_dtypes(include=[object]).columns:
        df[col] = df[col].str.replace(",", "", regex=False)

    df.to_excel(output[:-4] + ".xlsx", index=False)
    to_sqlite(df, output[:-4] + ".sqlite")

    print("Make sure to manually check the -ísimo cases!")
