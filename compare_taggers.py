# compares TagAnt (tagged) and stanza (stanza_tagged) tags token by token and writes the
# disagreements after an intensifier to tagger_disagreements.tsv for hand checking

import argparse
import difflib
import os
from collections import Counter

import pandas as pd

from step_7_tagged_to_csv import intensifier_list, is_adj, is_adv


def read_tags(path):
    tokens = []
    with open(path, encoding="utf-8") as f:
        for t in f.read().replace("_SPACE_", "").split():
            parts = t.split("_")
            if len(parts) >= 3:
                tokens.append((parts[0], parts[1], "_".join(parts[2:])))
    return tokens


def align(a, b):
    # stanza splits contractions (del -> de el), so only tokens with equal text are compared
    sm = difflib.SequenceMatcher(
        None, [t[0].lower() for t in a], [t[0].lower() for t in b], autojunk=False
    )
    return [(m.a + k, m.b + k) for m in sm.get_matching_blocks() for k in range(m.size)]


def host(token):
    tagged = "_".join(token)
    return "ADJ" if is_adj(tagged) else "ADV" if is_adv(tagged) else "-"


def context(tokens, i, width=8):
    left = " ".join(t[0] for t in tokens[max(0, i - width) : i])
    right = " ".join(t[0] for t in tokens[i + 1 : i + 1 + width])
    return f"{left} [[{tokens[i][0]}]] {right}"


def compare(tagant_dir, stanza_dir):
    pos = Counter()
    slots = []
    for name in sorted(os.listdir(tagant_dir)):
        if not name.endswith(".txt") or not os.path.exists(os.path.join(stanza_dir, name)):
            continue
        a = read_tags(os.path.join(tagant_dir, name))
        b = read_tags(os.path.join(stanza_dir, name))
        pairs = align(a, b)
        pos["tagant_tokens"] += len(a)
        pos["aligned"] += len(pairs)
        for i, j in pairs:
            pos["same_pos"] += a[i][1] == b[j][1]
            if i == 0 or a[i - 1][0].lower() not in intensifier_list:
                continue
            pos["after_int"] += 1
            ha, hb = host(a[i]), host(b[j])
            if ha != hb:
                slots.append({
                    "Speaker": name[:-4],
                    "Int": a[i - 1][0].lower(),
                    "Word": a[i][0].lower(),
                    "TagAnt": f"{a[i][1]}/{a[i][2]}",
                    "Stanza": f"{b[j][1]}/{b[j][2]}",
                    "TagAnt_host": ha,
                    "Stanza_host": hb,
                    "Context": context(a, i),
                })
    return pos, pd.DataFrame(slots)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tagant", default="tagged")
    parser.add_argument("--stanza", default="stanza_tagged")
    parser.add_argument("--out", default="tagger_disagreements.tsv")
    args = parser.parse_args()

    pos, slots = compare(args.tagant, args.stanza)
    print(f"aligned {pos['aligned']}/{pos['tagant_tokens']} TagAnt tokens")
    print(f"same POS {pos['same_pos'] / pos['aligned']:.1%}")
    print(f"tokens after an intensifier {pos['after_int']}, host decision differs on {len(slots)}")
    print(slots.groupby(["TagAnt_host", "Stanza_host"]).size().to_string())
    slots.to_csv(args.out, sep="\t", index=False)
    print(f"Saved {args.out}")
