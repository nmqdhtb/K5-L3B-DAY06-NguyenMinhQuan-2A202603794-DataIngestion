"""Validate benchmark evidence, splits, query isolation and frozen artifact hashes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate():
    read = lambda name: json.loads((ROOT / name).read_text(encoding='utf-8'))
    protocol = read('benchmark/protocol.json')
    for name, expected in protocol['frozen_files_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen artifact changed: {name}; review/version protocol explicitly')
    questions = read('benchmark/questions.json')
    pages = {(r['document_id'], r['page']): r for r in
             map(json.loads, (ROOT / 'data/processed/pages.jsonl').read_text(encoding='utf-8').splitlines())}
    ids = [q['id'] for q in questions]
    if len(ids) != len(set(ids)) or len(ids) < 20:
        raise ValueError('Need at least 20 unique question IDs')
    counts = {s: sum(q['split'] == s for q in questions) for s in ('dev', 'test')}
    if counts['dev'] < 15 or counts['test'] < 5 or sum(counts.values()) != len(questions):
        raise ValueError('Invalid split')
    filters = {'dev': 0, 'test': 0}
    for q in questions:
        page = pages[(q['gold_source_id'], q['gold_page'])]
        evidence = q['evidence_quote']
        offsets = q['evidence_offsets']
        if not q['expected_answer'].strip() or not evidence.strip():
            raise ValueError(f"Empty answer/evidence: {q['id']}")
        if page['text'][offsets['start']:offsets['end']] != evidence:
            raise ValueError(f"Evidence does not match page offsets: {q['id']}")
        f = q['filter']
        if f:
            if set(f) != {'verse_start', 'verse_end'} or set(f['verse_start']) != {'lte'} or set(f['verse_end']) != {'gte'}:
                raise ValueError('Unsupported filter schema')
            lower, upper = f['verse_end']['gte'], f['verse_start']['lte']
            if not 1 <= lower <= upper <= 3254:
                raise ValueError('Invalid requested verse interval')
            matching = [p for p in pages.values() if p['metadata']['verse_start'] <= upper
                        and p['metadata']['verse_end'] >= lower]
            if page not in matching or not 1 < len(matching) < len(pages):
                raise ValueError(f"Filter must include gold and narrow a multi-page scope: {q['id']}")
            filters[q['split']] += 1
    if sum(filters.values()) < 3 or filters['test'] < 1:
        raise ValueError('Need at least 3 filter questions, including 1 test')
    for split in counts:
        selected = [q for q in questions if q['split'] == split]
        if protocol['split'][split] != [q['id'] for q in selected]:
            raise ValueError('Protocol split mismatch')
        safe = [{k: q[k] for k in ('id', 'question', 'filter')} for q in selected]
        if read(f'benchmark/{split}_queries.json') != safe:
            raise ValueError('Query inputs changed or contain gold data')
    positions = read('benchmark/coherence_positions.json')
    if len(positions) != 10:
        raise ValueError('Need 10 coherence source positions')
    for p in positions:
        if not 0 <= p['character_offset'] < len(pages[(p['document_id'], p['page'])]['text']):
            raise ValueError('Invalid coherence position')
    reviews = read('benchmark/student_review.json')
    confirmed = (len(reviews) == len(ids)
                 and {r['question_id'] for r in reviews} == set(ids)
                 and all(r['status'] == 'confirmed_by_student'
                         and r['evidence_supports_answer'] is True
                         and r['source_page_checked'] is True for r in reviews))
    return {'status': 'passed', 'questions': len(questions), 'split_counts': counts,
            'filter_question_counts': filters, 'exact_evidence_matches': len(questions),
            'coherence_positions': len(positions), 'frozen_hashes_verified': True,
            'student_evidence_review': ('confirmed_by_student; self-reported in conversation'
                                        if confirmed else 'pending; not certified by this script'),
            'retrieval_metrics': 'not computed by this validation script'}


if __name__ == '__main__':
    result = validate()
    (ROOT / 'starter/results/benchmark_validation.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
