"""Build A/B chunks; C reuses B exactly. Does not read benchmark answers."""
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from statistics import mean, median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'starter'))
from src.chunking import fixed_size, by_paragraph
from src.models import DocumentPage


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    corpus = ROOT / 'data/processed/pages.jsonl'
    protocol = json.loads((ROOT / 'benchmark/protocol.json').read_text())
    digest = hashlib.sha256(corpus.read_bytes()).hexdigest()
    if digest != protocol['frozen_files_sha256']['data/processed/pages.jsonl']:
        raise ValueError('Corpus changed from frozen benchmark snapshot')
    pages = [DocumentPage(**json.loads(line)) for line in corpus.read_text().splitlines()]
    output = ROOT / 'starter/results/chunking'
    output.mkdir(parents=True, exist_ok=True)
    builds, stats = {}, {}
    for strategy, chunker in [('A', lambda p: fixed_size(p, 500, 50)),
                              ('B', lambda p: by_paragraph(p, 500))]:
        begin = perf_counter()
        chunks = []
        for page in pages:
            local = chunker(page)
            covered = [False] * len(page.text)
            for c in local:
                start, end = c.metadata['char_start'], c.metadata['char_end']
                if c.text != page.text[start:end] or not c.text.strip() or len(c.text) > 500:
                    raise ValueError('Invalid source span or empty/oversized chunk')
                if (c.document_id, c.source, c.page) != (page.document_id, page.source, page.page):
                    raise ValueError('Source metadata mismatch')
                for name in ('verse_start', 'verse_end'):
                    if c.metadata[name] != page.metadata[name]:
                        raise ValueError('Page-range filter metadata changed')
                covered[start:end] = [True] * (end - start)
            if not all(covered):
                raise ValueError(f'Content missing on page {page.page}')
            if strategy == 'B' and ''.join(c.text for c in local) != page.text:
                raise ValueError('Paragraph chunks do not reconstruct source exactly')
            chunks.extend(local)
        elapsed = perf_counter() - begin
        if len({c.chunk_id for c in chunks}) != len(chunks):
            raise ValueError('Duplicate chunk IDs')
        builds[strategy] = chunks
        lengths = [len(c.text) for c in chunks]
        path = output / f'chunks_{strategy}.jsonl'
        path.write_text(''.join(json.dumps(asdict(c), ensure_ascii=False) + '\n' for c in chunks), encoding='utf-8')
        stats[strategy] = {'chunk_count': len(chunks), 'min_characters': min(lengths),
                          'max_characters': max(lengths), 'mean_characters': mean(lengths),
                          'median_characters': median(lengths), 'total_characters': sum(lengths),
                          'build_and_validation_seconds': elapsed,
                          'length_bins': {f'{lo}-{hi}': sum(lo <= n <= hi for n in lengths)
                                          for lo, hi in [(1,100),(101,200),(201,300),(301,400),(401,500)]},
                          'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    stats['C'] = {**stats['B'], 'reuses': 'B', 'build_and_validation_seconds': None}
    strategies = {
        'A': {'chunk_file': 'chunks_A.jsonl', 'method': 'fixed', 'size_characters': 500,
              'overlap_characters': 50, 'apply_query_filter': False},
        'B': {'chunk_file': 'chunks_B.jsonl', 'method': 'paragraph', 'size_characters': 500,
              'overlap_characters': 0, 'apply_query_filter': False},
        'C': {'chunk_file': 'chunks_B.jsonl', 'method': 'paragraph', 'size_characters': 500,
              'overlap_characters': 0, 'apply_query_filter': True}}
    write_json(output / 'config.json', {'version': 1, 'corpus_sha256': digest, 'strategies': strategies,
                                       'embedding_model': None, 'vector_store': None,
                                       'status': 'chunking only; no retrieval metrics'})
    write_json(output / 'statistics.json', stats)
    positions = json.loads((ROOT / 'benchmark/coherence_positions.json').read_text())
    samples = []
    for strategy in ('A', 'B', 'C'):
        for pos in positions:
            candidates = [c for c in builds['B' if strategy == 'C' else strategy]
                          if c.document_id == pos['document_id'] and c.page == pos['page']
                          and c.metadata['char_start'] <= pos['character_offset'] < c.metadata['char_end']]
            if not candidates:
                raise ValueError('Missing coherence source position')
            # If overlapping windows cover a position, use the earliest start consistently.
            chosen = min(candidates, key=lambda c: c.metadata['char_start'])
            samples.append({'strategy': strategy, 'source_position': pos,
                            'chunk': asdict(chosen), 'score': None, 'reason': None, 'reviewer': None})
    # Never overwrite manual annotations on a later run.
    sample_path = output / 'coherence_review.json'
    if not sample_path.exists():
        write_json(sample_path, samples)
    else:
        existing = json.loads(sample_path.read_text())
        fields = ('strategy', 'source_position', 'chunk')
        if [{k: s[k] for k in fields} for s in existing] != [{k: s[k] for k in fields} for s in samples]:
            raise ValueError('Existing coherence samples differ; version the audit instead of overwriting')
    print(json.dumps({s: stats[s]['chunk_count'] for s in stats}, indent=2))


if __name__ == '__main__':
    main()
