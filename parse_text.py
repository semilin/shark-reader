import argparse
import json
import os
import re
import sys
import pandas as pd
import requests

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"

LANG_CONFIGS = {
    "latin": {
        "core_vocab": "./latin-core-list.csv",
        "name": "Latin",
        "lemma_instructions": "Put in primary principle parts (first person present active singular for verbs, nominative singular for nouns, etc.). Don't use macrons."
    },
    "greek": {
        "core_vocab": "./greek-core-list.csv",
        "name": "Ancient Greek",
        "lemma_instructions": "Put in primary principle parts (first person present active singular for verbs, nominative singular for nouns, etc.). Use proper polytonic accentuation."
    }
}

def query_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    response = requests.post(OLLAMA_URL, json=payload)
    if response.status_code == 200:
        return json.loads(response.json()["response"])
    else:
        raise Exception(f"Ollama error: {response.status_code} - {response.text}")

def clean_text(text):
    text = re.sub(r'\[\w+\]', '', text)
    text = re.sub(r'^[Α-Ωα-ω\s]+:', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[A-Z\s]+:', '', text, flags=re.MULTILINE)
    return text.strip()

def chunk_into_sentences(text):
    # Basic sentence splitter for Latin/Greek
    return re.split(r'(?<=[.?;·])\s+', text)

def lemmatize_sentence(sentence, config, vocab_list):
    prompt = (
        f"Context: {config['name']} literature.\n"
        f"Directions: Lemmatize every word in the following sentence. Return a JSON list of objects, "
        f"where each object has 'w' (original word with punctuation) and 'l' (dictionary lemma). "
        f"{config['lemma_instructions']}\n"
        f"Sentence: {sentence}\n"
        f"Example format: [{{'w': 'arma', 'l': 'arma'}}, {{'w': 'virumque', 'l': 'vir'}}, ...]"
    )
    try:
        res = query_ollama(prompt)
        # Handle cases where the model returns a dict with a key instead of a list
        if isinstance(res, dict):
            for val in res.values():
                if isinstance(val, list):
                    res = val
                    break
        
        # Post-process: check core status
        tokens = []
        for token in res:
            if 'w' not in token or 'l' not in token:
                continue
            
            lemma = token['l'].strip().lower()
            token['c'] = lemma in vocab_list
            tokens.append(token)
        return tokens
    except Exception as e:
        print(f"  Error lemmatizing: {e}")
        # Fallback: simple tokenization without lemmas
        return [{"w": w, "l": w.lower(), "c": False} for w in sentence.split()]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--lang", choices=["latin", "greek"], required=True)
    args = parser.parse_args()

    config = LANG_CONFIGS[args.lang]
    vocab_df = pd.read_csv(config["core_vocab"])
    vocab_list = set(vocab_df['Headword'].str.lower().tolist())

    with open(args.file, 'r', encoding='utf-8') as f:
        text = clean_text(f.read())

    sentences = chunk_into_sentences(text)
    annotated_text = []

    print(f"Processing {len(sentences)} sentences...")
    for i, sent in enumerate(sentences):
        if not sent.strip():
            continue
        print(f"Sent {i+1}/{len(sentences)}: {sent[:50]}...")
        tokens = lemmatize_sentence(sent, config, vocab_list)
        annotated_text.extend(tokens)

    out_file = f"{os.path.splitext(args.file)[0]}.annotated.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(annotated_text, f, ensure_ascii=False, indent=2)

    print(f"Done! Annotated text saved to {out_file}")

if __name__ == "__main__":
    main()
