# runs the whole pipeline: stanza tagging, correction and parse (annotate), then host extraction (extract)

import argparse
import os
from datetime import date

import dialects as dialect_rules
from annotate import correct_folder, parse_folder, parse_relations, tag_folder
from extract import analyze, write_outputs

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/text", help="folder of raw .txt transcripts")
    parser.add_argument("--tagged", default="data/stanza_tagged", help="where stanza output goes")
    parser.add_argument("--corrected", default="data/stanza_corrected", help="tags after correct_tokens")
    parser.add_argument("--parsed", default="data/stanza_parsed", help="dependency parse of the corrected tags")
    parser.add_argument("--speakers", help="speaker metadata sheet, one row per Speaker; omitted: no metadata columns")
    parser.add_argument(
        "--output",
        default="output/intensifier_data_stanza_" + date.today().isoformat(),
        help="output path without extension",
    )
    parser.add_argument(
        "--drop-invariant", action="store_true", help="drop every row of a host that is never intensified"
    )
    parser.add_argument("--xlsx", action="store_true", help="also write the table as xlsx")
    parser.add_argument("--csv", action="store_true", help="also write the table as csv")
    parser.add_argument(
        "--dialect",
        action="append",
        default=[],
        choices=sorted(dialect_rules.available),
        help="also apply this dialect's tag corrections (repeatable; the corpus needs pr and co)",
    )
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    tag_folder(args.input, args.tagged, args.workers)
    correct_folder(args.tagged, args.corrected, dialect_rules.load(args.dialect))
    parse_folder(args.corrected, args.parsed, args.workers)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    # Adj_type, Noun and Verb come from the dependency parse instead of word order
    df = analyze(args.corrected, None, parse_relations(args.parsed), drop_invariant=args.drop_invariant)
    write_outputs(df, args.output, args.speakers, xlsx=args.xlsx, csv=args.csv)

    print("Make sure to manually check the -ísimo cases!")
