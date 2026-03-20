import argparse
import json
import logging
import os
import sys
import concurrent.futures

import pandas as pd
from openai import OpenAI

from dolphindict import annotator, config, glossgen, tokenizer
from dolphindict.config import CONFIGS, DEFAULT_MAX_WORKERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_KEY:
    print("OPENROUTER_API_KEY environment variable must be set.")
    sys.exit(1)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)


def cmd_annotate(args):
    lang_config = CONFIGS[args.lang]

    with open(args.file, "r", encoding="utf-8") as f:
        full_text = f.read()

    print("Step 1: Cleaning and Tokenizing text...")
    full_text = tokenizer.clean_text(full_text)
    rich_tokens = tokenizer.tokenize_rich(full_text)

    word_pattern = tokenizer.get_word_pattern(lang_config.word_pattern)

    sentences = annotator.chunk_sentences(rich_tokens)

    print(
        f"Step 2: Annotating {len(sentences)} sentences in parallel (max_workers={DEFAULT_MAX_WORKERS})..."
    )

    results = [None] * len(sentences)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=DEFAULT_MAX_WORKERS
    ) as executor:
        future_to_idx = {}
        for idx, sent_indices in enumerate(sentences):
            sent_words = [
                rich_tokens[i]["w"] for i in sent_indices if rich_tokens[i]["t"] == "w"
            ]
            if sent_words:
                future = executor.submit(
                    annotator.get_annotated_sentence_lemmas,
                    sent_words,
                    lang_config,
                    client,
                    word_pattern,
                )
                future_to_idx[future] = idx

        completed = 0
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
            completed += 1
            if completed % 50 == 0 or completed == len(future_to_idx):
                print(f"  Completed {completed}/{len(future_to_idx)} sentences...")

    for idx, lemmas_res in enumerate(results):
        if lemmas_res is None:
            continue

        sent_indices = sentences[idx]
        word_idx_in_sent = 0
        for token_idx in sent_indices:
            if rich_tokens[token_idx]["t"] == "w":
                if word_idx_in_sent < len(lemmas_res):
                    rich_tokens[token_idx]["l"] = lemmas_res[word_idx_in_sent]["l"]
                else:
                    clean_word = word_pattern.sub(
                        "", rich_tokens[token_idx]["w"]
                    ).lower()
                    rich_tokens[token_idx]["l"] = clean_word
                word_idx_in_sent += 1

    out_anno = (
        args.out if args.out else f"{os.path.splitext(args.file)[0]}.annotated.json"
    )

    output_data = {
        "metadata": {
            "title": args.title
            if args.title
            else os.path.splitext(os.path.basename(args.file))[0],
            "author": args.author if args.author else "Unknown",
            "work_type": args.work_type,
            "language": args.lang,
        },
        "tokens": rich_tokens,
    }

    with open(out_anno, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"Annotated text saved to {out_anno}")


def cmd_repair(args):
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        tokens = data
        metadata = {
            "title": "Unknown",
            "author": "Unknown",
            "work_type": "prose",
            "language": args.lang,
        }
    else:
        tokens = data.get("tokens", [])
        metadata = data.get("metadata", {})

    print(f"Performing cleanup on {args.file}...")

    for t in tokens:
        if "w" in t:
            t["w"] = t["w"].replace("u2014", "—").replace("\xa0", " ").replace("\\", "")

    final_tokens = []
    for i, t in enumerate(tokens):
        if t["t"] == "p" and t["w"].isspace():
            continue
        if t["t"] == "p" and final_tokens and final_tokens[-1]["t"] == "w":
            final_tokens[-1]["w"] += t["w"]
        else:
            final_tokens.append(t)

    output_data = {"metadata": metadata, "tokens": final_tokens}
    with open(args.file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"Cleanup complete.")


def cmd_gloss(args):
    lang_config = CONFIGS[args.lang]
    vocab_df = pd.read_csv(lang_config.core_vocab)
    vocab_list = vocab_df["Headword"].str.lower().tolist()

    dict_path = (
        args.dict
        if args.dict
        else (
            "dictionaries/greek.json"
            if args.lang == "greek"
            else "dictionaries/latin.json"
        )
    )
    dictionary = {}
    if os.path.exists(dict_path):
        with open(dict_path, "r", encoding="utf-8") as f:
            try:
                dictionary = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse {dict_path}, starting fresh")

    encountered_lemmas = set()
    if args.input_json:
        with open(args.input_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            tokens = data if isinstance(data, list) else data.get("tokens", [])
            for t in tokens:
                if t["t"] == "w":
                    encountered_lemmas.add(t["l"])
    elif args.word:
        encountered_lemmas.add(args.word)
    else:
        print("Error: Must provide either --input-json or --word")
        return

    missing_lemmas = sorted(
        [
            l
            for l in encountered_lemmas
            if l and l.lower() not in vocab_list and l not in dictionary
        ]
    )

    print(f"Expanding dictionary ({len(missing_lemmas)} new lemmas)...")
    for i, lemma in enumerate(missing_lemmas):
        print(f"  [{i + 1}/{len(missing_lemmas)}] Generating gloss for '{lemma}'...")
        try:
            gloss = glossgen.generate_gloss(lemma, lang_config, vocab_list, client)
            dictionary[lemma] = gloss
            with open(dict_path, "w", encoding="utf-8") as f:
                json.dump(dictionary, f, ensure_ascii=False, indent=2)
        except glossgen.GlossGenerationError as e:
            print(f"    Error: {e}. Skipping...")
    print(f"Done! Dictionary '{dict_path}' updated.")


def main():
    parser = argparse.ArgumentParser(description="DolphinDict CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_anno = subparsers.add_parser(
        "annotate", help="Annotate a text file with lemmas and formatting"
    )
    parser_anno.add_argument("file", help="Input text file")
    parser_anno.add_argument("--lang", choices=["latin", "greek"], required=True)
    parser_anno.add_argument("--out", help="Output JSON path")
    parser_anno.add_argument("--title", help="Work title")
    parser_anno.add_argument("--author", help="Work author")
    parser_anno.add_argument(
        "--work-type",
        choices=["poem", "dialogue", "prose"],
        default="prose",
        help="Type of work",
    )
    parser_anno.set_defaults(func=cmd_annotate)

    parser_gloss = subparsers.add_parser(
        "gloss", help="Generate immersive glosses for missing words"
    )
    parser_gloss.add_argument("--lang", choices=["latin", "greek"], required=True)
    parser_gloss.add_argument(
        "--input-json", help="Annotated JSON file to scan for new words"
    )
    parser_gloss.add_argument("--word", help="Single word to generate gloss for")
    parser_gloss.add_argument("--dict", help="Dictionary file to update")
    parser_gloss.set_defaults(func=cmd_gloss)

    parser_repair = subparsers.add_parser(
        "repair", help="Fix misidentified tokens in an annotated file"
    )
    parser_repair.add_argument("file", help="Annotated JSON file to repair")
    parser_repair.add_argument("--lang", choices=["latin", "greek"], required=True)
    parser_repair.add_argument("--out", help="Output JSON path")
    parser_repair.add_argument(
        "--fix-offsets",
        action="store_true",
        help="Attempt to detect and fix lemma offsets",
    )
    parser_repair.set_defaults(func=cmd_repair)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
