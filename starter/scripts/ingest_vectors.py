"""Embed frozen chunks locally, persist A/B/C, and verify store behavior (no test queries)."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ['HF_HOME'] = str(ROOT / 'starter/.cache/huggingface')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import hashlib
import importlib.metadata
import json
import sys
import time
import uuid
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import psycopg
from psycopg import sql
from dotenv import load_dotenv
sys.path.insert(0, str(ROOT / 'starter'))
from src.embeddings import MyEmbedder
from src.models import Chunk
from src.store import PgVectorStore


def main():
    load_dotenv(ROOT / 'starter/.env')
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError('DATABASE_URL is missing; configure starter/.env')
    config = json.loads((ROOT / 'starter/embedding_config.json').read_text())
    chunk_dir = ROOT / 'starter/results/chunking'
    chunk_config = json.loads((chunk_dir / 'config.json').read_text())
    chunk_stats = json.loads((chunk_dir / 'statistics.json').read_text())
    if hashlib.sha256((ROOT / 'data/processed/pages.jsonl').read_bytes()).hexdigest() != chunk_config['corpus_sha256']:
        raise ValueError('Corpus changed; rebuild chunks explicitly')
    started = time.perf_counter()
    embedder = MyEmbedder(config['model_name'], config['revision'], ROOT / config['cache_folder'])
    if embedder.dimensions != config['dimensions'] or embedder.token_limit != config['max_sequence_tokens']:
        raise ValueError('Loaded model differs from pinned embedding configuration')
    signature = {k: config[k] for k in ['model_name', 'revision', 'pooling', 'query_document_processing', 'max_sequence_tokens']}
    store = PgVectorStore(url, embedder.dimensions, signature)
    store.create_schema()
    output = ROOT / 'starter/results/vector_ingestion'
    output.mkdir(parents=True, exist_ok=True)
    cache = ROOT / 'starter/.cache/embeddings'
    cache.mkdir(parents=True, exist_ok=True)
    batches, stats = {}, {}
    for strategy in ('A', 'B'):
        path = chunk_dir / chunk_config['strategies'][strategy]['chunk_file']
        chunk_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if chunk_hash != chunk_stats[strategy]['file_sha256']:
            raise ValueError('Chunk file changed since build')
        chunks = [Chunk(**json.loads(line)) for line in path.read_text().splitlines()]
        key = hashlib.sha256((chunk_hash + json.dumps(signature, sort_keys=True)).encode()).hexdigest()
        cached = cache / (key + '.npz')
        begin = time.perf_counter()
        if cached.exists():
            with np.load(cached, allow_pickle=False) as data:
                vectors = data['vectors'].tolist()
                token_stats = json.loads(str(data['token_stats'].item()))
            cache_hit = True
        else:
            vectors = embedder.embed_documents([c.text for c in chunks])
            token_stats = embedder.last_stats.copy()
            np.savez_compressed(cached, vectors=np.asarray(vectors, dtype=np.float32), token_stats=json.dumps(token_stats))
            cache_hit = False
        elapsed = time.perf_counter() - begin
        batches[strategy] = (chunks, vectors)
        stats[strategy] = {'embedding_or_cache_seconds': elapsed, 'cache_hit': cache_hit, **token_stats}
    batches['C'] = batches['B']
    stats['C'] = {'reuses_embeddings_from': 'B'}
    for strategy in ('A', 'B', 'C'):
        chunks, vectors = batches[strategy]
        begin = time.perf_counter()
        store.upsert(strategy, chunks, vectors)
        first = store.count(strategy)
        store.upsert(strategy, chunks, vectors)
        second = PgVectorStore(url, embedder.dimensions, signature).count(strategy)
        if first != len(chunks) or second != first:
            raise ValueError('Idempotent/persistent ingestion failed')
        stats[strategy].update(count_first=first, count_reingested=second,
                               upsert_twice_and_verify_seconds=time.perf_counter()-begin)
    # Smoke tests use a corpus vector as a probe, never test-set questions/gold.
    probe = batches['B'][1][0]
    b_hits = store.search('B', probe)
    c_hits = store.search('C', probe)
    if b_hits != c_hits or len(b_hits) != 3:
        raise ValueError('B/C without filter must return identical top-3')
    smoke = {'probe': 'embedding of first B chunk; not a benchmark question', 'B': b_hits, 'C_unfiltered': c_hits}
    for lower, upper in [(1,1000),(1001,2000),(2001,3254)]:
        filters = {'verse_start': {'lte': upper}, 'verse_end': {'gte': lower}}
        hits = store.search('C', probe, filters=filters)
        if len(hits) != 3 or not all(h['metadata']['verse_start'] <= upper and h['metadata']['verse_end'] >= lower for h in hits):
            raise ValueError('Filter smoke check failed')
        smoke[f'C_filter_{lower}_{upper}'] = hits
    # Stale-chunk deletion and rollback verified in an isolated temporary schema.
    scratch_name = 'day6_verify_' + uuid.uuid4().hex[:12]
    scratch = PgVectorStore(url, embedder.dimensions, signature, schema=scratch_name)
    scratch.create_schema()
    try:
        chunks, vectors = batches['B']
        scratch.upsert('A', chunks[:2], vectors[:2])
        scratch.upsert('A', chunks[1:2], vectors[1:2])
        if scratch.count('A') != 1 or scratch.search('A', vectors[1])[0]['chunk_id'] != chunks[1].chunk_id:
            raise ValueError('Obsolete chunk deletion failed')
        try:
            scratch.upsert('A', chunks[:1], [[float('nan')] * embedder.dimensions])
        except ValueError:
            pass
        else:
            raise ValueError('Non-finite vector accepted')
        if scratch.count('A') != 1:
            raise ValueError('Invalid input changed stored data')
        try:
            scratch.upsert('A', [chunks[0], replace(chunks[1], text=None)], vectors[:2])
        except psycopg.errors.NotNullViolation:
            pass
        else:
            raise ValueError('Expected database constraint rejection')
        if scratch.count('A') != 1 or scratch.search('A', vectors[1])[0]['chunk_id'] != chunks[1].chunk_id:
            raise ValueError('Partial write was not rolled back')
        try:
            PgVectorStore(url, embedder.dimensions, {'wrong_model': True}, schema=scratch_name).create_schema()
        except ValueError:
            pass
        else:
            raise ValueError('Mixed embedding model was accepted')
    finally:
        with store.connect() as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(scratch_name)))
    with store.connect() as conn:
        versions = conn.execute("SELECT current_setting('server_version'), extversion FROM pg_extension WHERE extname='vector'").fetchone()
    result = {'completed_at': datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(),
              'model': config, 'database': {'schema': store.schema, 'postgresql_version': versions[0],
              'pgvector_version': versions[1], 'metric': 'cosine', 'search': 'exact; no ANN index'},
              'strategies': stats, 'total_seconds': time.perf_counter()-started,
              'paid_api_cost_usd': 0, 'cost_scope': 'No paid API; excludes electricity, hardware and internet',
              'checks': {'reingestion_no_duplicates': True, 'new_connection_persistence': True,
                         'metadata_filter_three_ranges': True, 'B_C_unfiltered_identical': True,
                         'obsolete_chunk_removal': True, 'invalid_vector_rejected_without_mutation': True,
                         'transaction_rollback': True, 'different_model_rejected': True},
              'packages': {p: importlib.metadata.version(p) for p in ['sentence-transformers','transformers','torch','numpy','psycopg','pypdf']},
              'benchmark_run': False}
    for name, data in [('run.json', result), ('smoke_traces.json', smoke)]:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
