"""Evidence retrieval metrics; never infer manual coherence/grounding labels."""
from collections import defaultdict
import unicodedata
from typing import Any


def normalized_evidence(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', text).split())


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    golds = [{k: question[k] for k in ('gold_source_id', 'gold_page', 'evidence_quote')}]
    golds.extend(question.get('alternative_gold', []))
    if any(not normalized_evidence(g['evidence_quote']) for g in golds):
        raise ValueError('Gold evidence must not be empty')
    evaluated = []
    for rank, hit in enumerate(hits[:3], 1):
        text = normalized_evidence(hit['text'])
        matches = [i for i, gold in enumerate(golds)
                   if hit['document_id'] == gold['gold_source_id']
                   and hit['page'] == gold['gold_page']
                   and normalized_evidence(gold['evidence_quote']) in text]
        evaluated.append({**hit, 'rank': rank, 'evidence_hit': bool(matches), 'matched_gold_indices': matches})
    return {'question_id': question['id'], 'split': question['split'], 'question': question['question'],
            'expected_answer': question['expected_answer'], 'gold_evidence': golds,
            'requested_filter': question.get('filter'), 'hits': evaluated,
            'hit1': bool(evaluated and evaluated[0]['evidence_hit']),
            'hit3': any(h['evidence_hit'] for h in evaluated),
            'evaluation_method': 'source + physical page + complete NFC/whitespace-normalized evidence substring',
            'manual_grounding': None}


def summarize(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = defaultdict(list)
    seen = set()
    for trace in traces:
        key = (trace['strategy'], trace['split'], trace['question_id'])
        if key in seen:
            raise ValueError('Duplicate strategy/split/question trace')
        seen.add(key)
        groups[key[:2]].append(trace)
    rows = []
    for (strategy, split), group in sorted(groups.items()):
        n = len(group)
        h1, h3 = sum(t['hit1'] for t in group), sum(t['hit3'] for t in group)
        rows.append({'strategy': strategy, 'split': split, 'question_count': n,
                     'hit1_numerator': h1, 'hit3_numerator': h3, 'hit1': h1/n, 'hit3': h3/n})
    return rows
