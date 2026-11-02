# scores an output table's adjective rows against a hand-labelled sample

import argparse
import sqlite3

import pandas as pd

key = ["Speaker", "Phr", "Adj", "Int"]


def score(gold, output):
    """score returns counts of tagger and Adj_type errors for the gold rows found in output."""
    out = output.drop_duplicates(key)[key + ["Adj_type"]]
    merged = gold.merge(out, on=key, how="left")
    found = merged[merged["Adj_type"].notna()]
    real = found[found["gold_adj"] == "y"]
    clear = real[real["gold_type"] != "unclear"]
    decided = clear[clear["Adj_type"] != "ambiguous"]
    return {
        "gold rows": len(gold),
        "found in output": len(found),
        "not really ADJ": int((found["gold_adj"] == "n").sum()),
        "real ADJ, clear Adj_type": len(clear),
        "right": int((decided["Adj_type"] == decided["gold_type"]).sum()),
        "wrong": int((decided["Adj_type"] != decided["gold_type"]).sum()),
        "left ambiguous": len(clear) - len(decided),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="intensifier_data_*.sqlite")
    parser.add_argument("--gold", required=True, help="hand-labelled sample (tsv)")
    args = parser.parse_args()
    gold = pd.read_csv(args.gold, sep="\t", keep_default_na=False)
    output = pd.read_sql("SELECT * FROM intensifier_data", sqlite3.connect(args.output))
    counts = score(gold, output)
    for name, n in counts.items():
        print(f"{name:26} {n}")
    clear = counts["real ADJ, clear Adj_type"]
    if clear:
        print(f"{'Adj_type right':26} {counts['right'] / clear:.1%}")
