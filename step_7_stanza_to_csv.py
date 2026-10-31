# tags the raw transcripts with stanza instead of TagAnt, then runs the same extraction as step 7

import argparse
import os
import re
from datetime import date
from multiprocessing import Pool

import pandas as pd

from step_7_tagged_to_csv import (
    analyze,
    closest_verb_infinitive,
    closest_verb_non_infinitive,
    count_syllables,
    intensifier_list,
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

# plural -es stripped one letter too far (chéveres -> chéver)
lemma_fixes = {"chéver": "chévere", "chever": "chevere"}

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


# verbs that take a predicative adjective, so "se puso peor" / "sigue igual" stay ADJ
predicative_lemmas = {"ser", "estar", "parecer", "poner", "sentir", "ver", "quedar", "volver", "encontrar", "dejar", "hallar", "seguir"}
clitics = {"me", "te", "se", "nos", "le", "les", "lo", "la", "los", "las"}
possessives = {
    p + e for p in ("mí", "tuy", "suy", "nuestr", "vuestr") for e in ("o", "a", "os", "as")
}
comparatives = {"mejor", "mejores", "peor", "peores", "mayor", "mayores", "menor", "menores"}
_edge = ("", "PUNCT", "")


def _around(tokens, i):
    prev = tokens[i - 1] if i > 0 else _edge
    nxt = tokens[i + 1] if i + 1 < len(tokens) else _edge
    nxt2 = tokens[i + 2] if i + 2 < len(tokens) else _edge
    return prev, nxt, nxt2


def _before_verb(nxt, nxt2):
    return nxt[1] in ("VERB", "AUX") or (nxt[0].lower() in clitics and nxt2[1] in ("VERB", "AUX"))


def _adverbial_comparative(tokens, i):
    # "mejor dicho", "a lo mejor", "mejor me voy", "vive mejor" vs "el mejor", "es mejor", "futuro mejor"
    prev, nxt, nxt2 = _around(tokens, i)
    if nxt[0].lower() == "dicho" or (prev[0].lower() == "lo" and i > 1 and tokens[i - 2][0].lower() == "a"):
        return True
    if (
        prev[1] in ("DET", "NOUN", "PROPN", "AUX")
        or prev[2] in predicative_lemmas
        or prev[0].lower() in ("lo", "mucho", "muchísimo", "tanto", "como", "algo", "nada")
    ):
        return False
    return _before_verb(nxt, nxt2) or (prev[1] == "VERB" and nxt[1] not in ("NOUN", "PROPN"))


def _adverbial_igual(tokens, i):
    # "pero igual se fue" (anyway) vs "es igual", "igual a", "igual forma"
    prev, nxt, nxt2 = _around(tokens, i)
    if nxt[1] in ("NOUN", "PROPN") or nxt[0].lower() in ("a", "al", "de", "en"):
        return False
    if prev[1] in ("NOUN", "PROPN") and _before_verb(nxt, nxt2):
        return True
    return not (
        prev[1] in ("DET", "NOUN", "PROPN", "AUX", "ADP")
        or prev[2] in predicative_lemmas
        or prev[0].lower() in intensifier_list + ["lo", "tan", "más", "todo"]
    )


def _discourse_slot(tokens, i):
    # clause-initial and not before a noun: "bueno, ...", "y bueno eso fue", "claro que sí"
    prev, nxt, _ = _around(tokens, i)
    return nxt[1] not in ("NOUN", "PROPN") and (
        prev[1] in ("PUNCT", "CCONJ", "INTJ")
        or prev[0].lower() in ("sí", "pues", "porque", "no", "ah", "ay", "eh", "y", "o", "pero")
    )


def _quantified_noun(tokens, i):
    # "hay mucho venezolano", "mucho extranjero": mucho is a quantifier, so the ADJ is a noun
    if i == 0 or tokens[i - 1][0].lower() != "mucho" or tokens[i][0].lower() in comparatives:
        return False
    return tokens[i - 1][1] == "DET" or (i > 1 and tokens[i - 2][2] == "haber")


def correct_tokens(tokens):
    """correct_tokens fixes Stanza's closed list of systematic errors found in tagger_comparison.md."""
    out = []
    for i, (text, upos, lemma) in enumerate(tokens):
        low = text.lower()
        after_int = i > 0 and tokens[i - 1][0].lower() in intensifier_list
        if after_int and low == "poco" and upos == "PRON":
            upos = "ADV"
        # "mucho solo" is quantifier + "only", not intensified "lonely"
        elif after_int and low == "solo" and upos == "ADV" and tokens[i - 1][0].lower() != "mucho":
            upos, lemma = "ADJ", "solo"
        elif upos == "ADJ" and text[0].isupper() and low in ("san", "santa", "santo", "santos", "santas"):
            upos = "PROPN"
        elif upos == "ADJ" and low in ("bueno", "claro") and not after_int and _discourse_slot(tokens, i):
            upos = "INTJ"
        elif upos == "ADJ" and low in ("mejor", "peor") and _adverbial_comparative(tokens, i):
            upos = "ADV"
        elif low == "dicho" and i > 0 and tokens[i - 1][0].lower() == "mejor":
            upos, lemma = "VERB", "decir"
        elif upos == "ADJ" and low == "igual" and _adverbial_igual(tokens, i):
            upos = "ADV"
        elif upos == "ADJ" and low in possessives:
            upos = "DET"
        elif upos == "ADJ" and _quantified_noun(tokens, i):
            upos = "NOUN"
        elif upos == "ADJ" and re.search(r"(d|t|ch|s)[oa]s?$", low) and re.search(r"[aeií]r$", lemma):
            # participles get the verb as lemma (dado -> dar), but Lex_Adj wants the adjective
            lemma = re.sub(r"[oa]s?$", "o", low)
        out.append((text, upos, lemma_fixes.get(lemma, lemma)))
    return out


def correct_line(line):
    tokens = []
    for t in line.split():
        text, upos, lemma = t.split("_", 2)
        tokens.append((text, upos, lemma))
    return " ".join("_".join(t) for t in correct_tokens(tokens))


def correct_folder(input_folder, output_folder):
    # raw tagger output stays untouched so it can still be compared against TagAnt
    os.makedirs(output_folder, exist_ok=True)
    for name in sorted(os.listdir(input_folder)):
        if not name.endswith(".txt"):
            continue
        with open(os.path.join(input_folder, name), encoding="utf-8") as f:
            lines = [correct_line(line) for line in f.read().splitlines()]
        with open(os.path.join(output_folder, name), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


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
    parser.add_argument("--corrected", default="stanza_corrected", help="tags after correct_tokens")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    tag_folder(args.input, args.tagged, args.workers)
    correct_folder(args.tagged, args.corrected)

    output = "intensifier_data_stanza_" + date.today().isoformat() + ".csv"
    df = analyze(args.corrected, output)

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
