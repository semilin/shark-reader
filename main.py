import argparse
import json
import logging
import os
import sys
import concurrent.futures

import pandas as pd
from openai import OpenAI

from sharkreader import annotator, config, glossgen, tokenizer
from sharkreader.config import CONFIGS, DEFAULT_MAX_WORKERS

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
    """Annotate an existing JSON file with lemmas for words missing them."""
    lang_config = CONFIGS[args.lang]
    word_pattern = tokenizer.get_word_pattern(lang_config.word_pattern)

    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)

    tokens = data.get("tokens", [])

    # Group words by sentence for parallel annotation
    sentences = annotator.chunk_sentences(tokens)

    # Only process words that don't have lemmas yet
    sentences_to_annotate = []
    for sent_indices in sentences:
        words_needing_lemma = [
            (i, tokens[i]["w"])
            for i in sent_indices
            if tokens[i].get("t") == "w" and not tokens[i].get("l")
        ]
        if words_needing_lemma:
            sentences_to_annotate.append(words_needing_lemma)

    print(
        f"Annotating {len(sentences_to_annotate)} sentences with {len(sum(sentences_to_annotate, []))} words..."
    )

    results = [None] * len(sentences_to_annotate)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=DEFAULT_MAX_WORKERS
    ) as executor:
        future_to_idx = {}
        for idx, word_indices in enumerate(sentences_to_annotate):
            sent_words = [w for _, w in word_indices]
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

    # Apply lemmas to tokens
    for idx, lemmas_res in enumerate(results):
        if lemmas_res is None:
            continue

        word_indices = sentences_to_annotate[idx]
        for word_idx_in_sent, (token_idx, _) in enumerate(word_indices):
            if word_idx_in_sent < len(lemmas_res):
                tokens[token_idx]["l"] = lemmas_res[word_idx_in_sent]["l"]

    out_path = args.out if args.out else args.file

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Annotated text saved to {out_path}")


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


import xml.etree.ElementTree as ET


def cmd_from_xml(args):
    import unicodedata
    import re

    tree = ET.parse(args.file)
    root = tree.getroot()

    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    title_elem = root.find(".//tei:titleStmt/tei:title", ns)
    title = title_elem.text if title_elem is not None else "Unknown"
    if title_elem is not None and title_elem.get("xml:lang") == "grc":
        title = title_elem.text if title_elem.text else "Unknown"

    author_elem = root.find(".//tei:titleStmt/tei:author", ns)
    author = author_elem.text if author_elem is not None else "Unknown"

    lang_elem = root.find(".//tei:language", ns)
    lang = (
        "greek"
        if lang_elem is not None and lang_elem.get("ident") == "grc"
        else "greek"
    )

    text_body = root.find(".//tei:text/tei:body", ns)
    if text_body is None:
        print("Error: Could not find text body in XML")
        return

    tokens: list[dict] = []

    LATIN_EXTENDED = "\u00c0-\u017f"
    GREEK_RANGE = "\u0370-\u03ff\u1f00-\u1fff"
    WORD_PATTERN = re.compile(rf"[\w{LATIN_EXTENDED}{GREEK_RANGE}]+")

    def add_token(t: str, w: str, l: str = ""):
        tokens.append({"t": t, "w": w, "l": l})

    def process_text_content(text: str):
        """Process text content, preserving order of words and punctuation.

        Punctuation attached to words is merged into the word token (w field),
        but the lemma (l field) is the clean word without punctuation.
        """
        PUNCT_CHARS = set(".,;:!?'\"‑–—()[]{}⟨⟩«»")

        pos = 0
        while pos < len(text):
            # Try to match a word
            word_match = WORD_PATTERN.match(text, pos)
            if word_match:
                word = word_match.group()
                if word:
                    # Look ahead for trailing punctuation to merge with word
                    end_pos = word_match.end()
                    while end_pos < len(text) and (
                        not WORD_PATTERN.match(text, end_pos)
                        and text[end_pos] in PUNCT_CHARS
                    ):
                        end_pos += 1

                    # Get the text including potential punctuation
                    full_word = text[word_match.start() : end_pos]

                    # Leave lemma blank - LLM annotation will fill it in
                    add_token("w", full_word, "")
                    pos = end_pos

                    # Handle any remaining trailing whitespace/punctuation
                    while pos < len(text) and text[pos] in PUNCT_CHARS:
                        add_token("p", text[pos], "")
                        pos += 1
            elif text[pos] in "\n\t":
                add_token("n", "", "")
                pos += 1
            else:
                # Standalone punctuation
                if text[pos] in PUNCT_CHARS:
                    add_token("p", text[pos], "")
                    pos += 1
                else:
                    pos += 1

    def process_element(elem):
        tag = elem.tag.replace("{http://www.tei-c.org/ns/1.0}", "")

        if tag == "div":
            div_type = elem.get("type")
            div_n = elem.get("n", "")
            if div_type == "textpart" and div_n:
                add_token("m", f"[{div_n}]", "")
                add_token("n", "", "")
            for child in elem:
                process_element(child)

        elif tag == "p":
            for child in elem:
                process_element(child)
            add_token("n", "", "")

        elif tag == "sp":
            # Speech container - process children (speaker and lines)
            for child in elem:
                process_element(child)
            add_token("n", "", "")

        elif tag == "speaker":
            # Speaker name - add as speaker token
            if elem.text:
                speaker = elem.text.strip()
                if speaker:
                    add_token("s", speaker + ":", "")

        elif tag == "l":
            # Line of verse - process text content and children (like add, del, gap)
            if elem.text:
                process_text_content(elem.text)
            for child in elem:
                process_element(child)
            add_token("n", "", "")

        elif tag == "said":
            who = elem.get("who", "")
            if who:
                speaker = who.replace("#", "") + ":"
                add_token("s", speaker, "")
            for child in elem:
                process_element(child)
            add_token("n", "", "")

        elif tag == "label":
            # Skip label elements (abbreviated speaker names like ΣΩ., ΚΡ.)
            # The full speaker name is already in the said element's "who" attribute
            pass

        elif tag == "milestone":
            unit = elem.get("unit")
            n = elem.get("n", "")
            if unit == "section" and n:
                add_token("m", f"[{n}]", "")
            elif unit == "page":
                pass

        elif tag == "q":
            for child in elem:
                process_element(child)

        elif tag == "note":
            # Skip note elements (editorial notes, cast lists, etc.)
            pass

        elif tag == "del":
            # Deleted text - skip (don't include in output)
            pass

        elif tag == "add":
            # Added text - process children
            for child in elem:
                process_element(child)

        elif tag == "gap":
            # Gap in text - add placeholder
            add_token("p", "[...]", "")

        elif elem.text:
            process_text_content(elem.text)

        if elem.tail:
            process_text_content(elem.tail)

    for child in text_body:
        process_element(child)

    output_data = {
        "metadata": {
            "title": args.title if args.title else title,
            "author": args.author if args.author else author,
            "work_type": args.work_type,
            "language": lang,
        },
        "tokens": tokens,
    }

    out_path = (
        args.out if args.out else f"{os.path.splitext(args.file)[0]}.annotated.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"Converted XML to {out_path}")
    print(f"Note: Run 'python main.py annotate {out_path} --lang {lang}' to add lemmas")


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
        [l for l in encountered_lemmas if l and l not in dictionary]
    )

    print(f"Expanding dictionary ({len(missing_lemmas)} new lemmas)...")

    if not missing_lemmas:
        print("No new lemmas to add.")
        return

    results = {}

    # Timeout for each gloss generation task
    TASK_TIMEOUT = 90  # seconds

    # Process in smaller batches to avoid hanging
    batch_size = DEFAULT_MAX_WORKERS
    for i in range(0, len(missing_lemmas), batch_size):
        batch = missing_lemmas[i : i + batch_size]

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as executor:
            future_to_lemma = {
                executor.submit(
                    glossgen.generate_gloss, lemma, lang_config, vocab_list, client
                ): lemma
                for lemma in batch
            }

            for future in concurrent.futures.as_completed(future_to_lemma):
                lemma = future_to_lemma[future]
                try:
                    gloss = future.result(timeout=TASK_TIMEOUT)
                    results[lemma] = gloss
                except concurrent.futures.TimeoutError:
                    print(f"    Timeout generating gloss for '{lemma}'. Skipping...")
                except glossgen.GlossGenerationError as e:
                    print(f"    Error generating gloss for '{lemma}': {e}. Skipping...")
                except Exception as e:
                    print(f"    Unexpected error for '{lemma}': {e}. Skipping...")

        completed = min(i + batch_size, len(missing_lemmas))
        print(f"  Completed {completed}/{len(missing_lemmas)} glosses...")

    # Save dictionary once with all results
    dictionary.update(results)
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=2)
    print(f"Done! Dictionary '{dict_path}' updated with {len(results)} new entries.")


def main():
    parser = argparse.ArgumentParser(description="SharkReader CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_anno = subparsers.add_parser(
        "annotate", help="Annotate a JSON file with lemmas for missing words"
    )
    parser_anno.add_argument("file", help="Input JSON file (from from-xml)")
    parser_anno.add_argument("--lang", choices=["latin", "greek"], required=True)
    parser_anno.add_argument(
        "--out", help="Output JSON path (default: overwrite input)"
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

    parser_xml = subparsers.add_parser(
        "from-xml", help="Convert TEI XML (Perseus) to annotated JSON"
    )
    parser_xml.add_argument("file", help="Input XML file")
    parser_xml.add_argument("--out", help="Output JSON path")
    parser_xml.add_argument("--title", help="Work title (overrides XML)")
    parser_xml.add_argument("--author", help="Work author (overrides XML)")
    parser_xml.add_argument(
        "--work-type",
        choices=["poem", "dialogue", "prose"],
        default="dialogue",
        help="Type of work",
    )
    parser_xml.set_defaults(func=cmd_from_xml)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
