"""Search a prepared local index; this command does not calculate benchmark scores."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
os.environ['HF_HOME'] = str(ROOT / 'starter/.cache/huggingface')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
sys.path.insert(0, str(ROOT / 'starter'))
from dotenv import load_dotenv
from src.embeddings import MyEmbedder
from src.store import PgVectorStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--question', required=True)
    parser.add_argument('--strategy', choices=['A','B','C'], default='C')
    parser.add_argument('--verse-range', nargs=2, type=int, metavar=('START','END'))
    args = parser.parse_args()
    if not args.question.strip():
        parser.error('Question cannot be empty')
    if args.verse_range and (args.strategy != 'C' or not 1 <= args.verse_range[0] <= args.verse_range[1] <= 3254):
        parser.error('Verse range requires strategy C and 1 <= START <= END <= 3254')
    load_dotenv(ROOT / 'starter/.env')
    config = json.loads((ROOT / 'starter/embedding_config.json').read_text())
    embedder = MyEmbedder(config['model_name'], config['revision'], ROOT / config['cache_folder'])
    signature = {k: config[k] for k in ['model_name','revision','pooling','query_document_processing','max_sequence_tokens']}
    store = PgVectorStore(os.environ['DATABASE_URL'], embedder.dimensions, signature)
    store.create_schema()
    filters = None
    if args.verse_range:
        filters = {'verse_start': {'lte': args.verse_range[1]}, 'verse_end': {'gte': args.verse_range[0]}}
    query = embedder.embed_query(args.question)
    hits = store.search(args.strategy, query, filters=filters)
    print(json.dumps({'question':args.question,'strategy':args.strategy,'filter':filters,'hits':hits},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
