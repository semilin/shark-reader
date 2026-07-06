"""SharkReader v2 CLI entry point.

Single `pipeline` command runs all three phases in order; each is idempotent
(re-running skips already-finished work). Granular flags allow re-runs of a
single phase:

    python main_v2.py pipeline <file.json> --lang greek
    python main_v2.py pipeline <file.json> --lang greek --lemmatize-only
    python main_v2.py pipeline <file.json> --lang greek --gloss-only
    python main_v2.py pipeline <file.json> --lang greek --substitute-only

The `--keep-cache` flag retains the *.substitutes.cache.json file after a
successful run so a subsequent run can resume without rebilling processed
occurrences.
"""

import argparse
import logging
import sys

from sharkreader.v2.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="SharkReader v2 pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("pipeline", help="Run the v2 annotation pipeline")
    p.add_argument(
        "file",
        help="Annotated JSON file OR Perseus TEI XML file (.xml triggers parsing)",
    )
    p.add_argument(
        "--lang", choices=["latin", "greek"], required=True,
    )
    p.add_argument(
        "--out", help="Output JSON path (default: overwrite input, or <stem>.annotated.json for XML)",
    )
    p.add_argument(
        "--dict", help="Dictionary JSON path (default: web/static/dictionaries/<lang>.json)",
    )
    p.add_argument(
        "--lemmatize-only", action="store_true",
        help="Run only phase 1 (lemmatize)",
    )
    p.add_argument(
        "--gloss-only", action="store_true",
        help="Run only phase 2 (gloss)",
    )
    p.add_argument(
        "--substitute-only", action="store_true",
        help="Run only phase 3 (substitute)",
    )
    p.add_argument(
        "--keep-cache", action="store_true",
        help="Keep the *.substitutes.cache.json file after a successful run",
    )
    p.add_argument(
        "--work-type", choices=["poem", "dialogue", "prose"], default="prose",
        help="Work type for XML parsing (ignored for JSON input)",
    )
    p.add_argument(
        "--title", help="Override work title (XML input only)",
    )
    p.add_argument(
        "--author", help="Override work author (XML input only)",
    )
    p.set_defaults(func=_run)

    args = parser.parse_args()
    args.func(args)


def _run(args: argparse.Namespace) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Convert --*-only into the three enable flags.
    only_flags = [
        args.lemmatize_only, args.gloss_only, args.substitute_only,
    ]
    if any(only_flags):
        lemmatize, gloss, substitute = only_flags
    else:
        lemmatize = gloss = substitute = True

    run_pipeline(
        args.file,
        lang=args.lang,
        lemmatize=lemmatize,
        gloss=gloss,
        substitute=substitute,
        dictionary_path=args.dict,
        keep_cache=args.keep_cache,
        out_path=args.out,
        work_type=args.work_type,
        title=args.title,
        author=args.author,
    )


if __name__ == "__main__":
    main()