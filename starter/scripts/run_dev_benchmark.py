"""Run DEV only, preserve top-3 traces and freeze the strategy selected by preregistered rules."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ['HF_HOME'] = str(ROOT / 'starter/.cache/huggingface')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import csv
import hashlib
import json
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from psycopg import sql
from dotenv import load_dotenv
sys.path.insert(0, str(ROOT / 'starter'))
from src.embeddings import MyEmbedder
from src.store import PgVectorStore
from src.evaluation import evaluate_query, summarize
from validate_benchmark import validate


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')


def main():
    if (ROOT / 'benchmark/selected_strategy.json').exists():
        raise ValueError('A strategy is already frozen; version any new dev experiment explicitly')
    validation = validate()
    if not validation['student_evidence_review'].startswith('confirmed_by_student'):
        raise ValueError('Student evidence verification is still pending')
    protocol = read('benchmark/protocol.json')
    expected_rule = ['Highest dev Evidence Hit@3','Then highest dev Hit@1','Then fewer indexed chunks','Then alphabetical strategy ID for deterministic final tie']
    if protocol['selection_rule'] != expected_rule:
        raise ValueError('Selection rule changed; implement the declared rule before running')
    config = read('starter/embedding_config.json')
    chunk_config = read('starter/results/chunking/config.json')
    ingestion = read('starter/results/vector_ingestion/run.json')
    if ingestion['model'] != config:
        raise ValueError('Model config differs from completed ingestion')
    load_dotenv(ROOT / 'starter/.env')
    signature = {k: config[k] for k in ['model_name','revision','pooling','query_document_processing','max_sequence_tokens']}
    store = PgVectorStore(os.environ['DATABASE_URL'],config['dimensions'],signature)
    # Read-only check of the database model and every chunk's source content/metadata.
    with store.connect() as conn:
        saved = conn.execute(sql.SQL('SELECT signature FROM {} WHERE id=1').format(store.config)).fetchone()[0]
        if saved != {**signature,'dimensions':config['dimensions']}:
            raise ValueError('Stored model differs from selected embedder')
        snapshots = {}
        counts = {}
        for strategy in ('A','B','C'):
            path = ROOT/'starter/results/chunking'/chunk_config['strategies'][strategy]['chunk_file']
            expected = {c['chunk_id']:c for c in map(json.loads,path.read_text().splitlines())}
            rows=conn.execute(sql.SQL('SELECT chunk_id,document_id,source,page,text,metadata FROM {} WHERE strategy=%s').format(store.table),(strategy,)).fetchall()
            actual={r[0]:dict(chunk_id=r[0],document_id=r[1],source=r[2],page=r[3],text=r[4],metadata=r[5]) for r in rows}
            if actual != expected:
                raise ValueError(f'Database snapshot mismatch: {strategy}')
            snapshots[strategy]=list(actual.values()); counts[strategy]=len(actual)
    # Embedding/retrieval receives only query file fields. Gold is used exclusively by scoring.
    queries=read('benchmark/dev_queries.json')
    golds={q['id']:q for q in read('benchmark/questions.json') if q['split']=='dev'}
    if [q['id'] for q in queries] != protocol['split']['dev'] or set(golds)!=set(protocol['split']['dev']):
        raise ValueError('Dev query/gold IDs do not match protocol')
    started=time.perf_counter()
    embedder=MyEmbedder(config['model_name'],config['revision'],ROOT/config['cache_folder'])
    if (embedder.dimensions,embedder.token_limit)!=(config['dimensions'],config['max_sequence_tokens']):
        raise ValueError('Unexpected model shape/token limit')
    begin=time.perf_counter()
    vectors=embedder.embed_documents([q['question'] for q in queries])
    embedding_seconds=time.perf_counter()-begin
    traces=[]
    for strategy in ('A','B','C'):
        for q,vector in zip(queries,vectors):
            filters=q['filter'] if strategy=='C' else None
            begin=time.perf_counter()
            hits=store.search(strategy,vector,top_k=3,filters=filters)
            elapsed=time.perf_counter()-begin
            trace=evaluate_query(golds[q['id']],hits)
            trace.update(strategy=strategy,applied_filter=filters,search_seconds=elapsed)
            if q['filter']:
                f=q['filter']
                trace['requested_filter_top3_compliant']=bool(hits) and all(h['metadata']['verse_start']<=f['verse_start']['lte'] and h['metadata']['verse_end']>=f['verse_end']['gte'] for h in hits)
            else:
                trace['requested_filter_top3_compliant']=None
            if not trace['hit3']:
                # Diagnostic about evidence coverage, NOT a manual grounding label.
                covered=any(evaluate_query(golds[q['id']],[c])['hit1'] for c in snapshots[strategy])
                trace['miss_diagnostic']='full_evidence_exists_but_not_in_top3' if covered else 'no_single_chunk_contains_full_gold_evidence'
            else:
                trace['miss_diagnostic']=None
            traces.append(trace)
    metrics=summarize(traces)
    for row in metrics:
        group=[t for t in traces if t['strategy']==row['strategy']]
        filtered=[t for t in group if t['requested_filter']]
        row.update(chunk_count=counts[row['strategy']],search_seconds=sum(t['search_seconds'] for t in group),
                   filter_question_count=len(filtered),filter_top3_compliant_count=sum(t['requested_filter_top3_compliant'] for t in filtered))
    winner=sorted(metrics,key=lambda r:(-r['hit3_numerator'],-r['hit1_numerator'],r['chunk_count'],r['strategy']))[0]['strategy']
    now=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
    output=ROOT/'starter/results/benchmark/dev'/now.strftime('%Y%m%dT%H%M%S%f')
    output.mkdir(parents=True,exist_ok=False)
    (output/'traces.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces),encoding='utf-8')
    write(output/'metrics.json',metrics)
    with (output/'metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(metrics[0]),lineterminator='\n');w.writeheader();w.writerows(metrics)
    write(output/'run.json',{'completed_at':now.isoformat(),'split':'dev','query_count':len(queries),'trace_count':len(traces),
         'query_embedding_seconds_shared_by_all_strategies':embedding_seconds,'query_embedding_stats':embedder.last_stats,
         'total_seconds_excluding_imports':time.perf_counter()-started,'paid_api_cost_usd':0,
         'model':config,'store':ingestion['database'],'test_run':False})
    paths=['starter/embedding_config.json','starter/results/chunking/config.json','starter/results/chunking/chunks_A.jsonl',
           'starter/results/chunking/chunks_B.jsonl','starter/src/embeddings.py','starter/src/store.py','starter/src/evaluation.py',
           'starter/src/chunking.py','starter/scripts/run_dev_benchmark.py','starter/requirements-lock.txt']
    hashes={**protocol['frozen_files_sha256'],**{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    selected={'selected_strategy':winner,'selected_at':now.isoformat(),'selection_rule':protocol['selection_rule'],
              'dev_metrics':metrics,'dev_run_directory':str(output.relative_to(ROOT)),
              'test_run':False,'frozen_files_sha256':hashes,
              'reason':'Highest dev Hit@3, then Hit@1, then fewer chunks, then alphabetical strategy ID; no test results used.'}
    write(ROOT/'benchmark/selected_strategy.json',selected)
    log=ROOT/'artifacts/experiment_log.csv'
    with log.open() as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;entries=list(reader)
    for entry in entries:
        row=next(r for r in metrics if r['strategy']==entry['strategy'])
        entry['dev_hit1']=f"{row['hit1_numerator']}/{row['question_count']}"
        entry['dev_hit3']=f"{row['hit3_numerator']}/{row['question_count']}"
        entry['notes']=f"Dev đã chạy; test chưa chạy. Chọn {winner} theo protocol. Kết quả: {output.relative_to(ROOT)}"
    with log.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(entries)
    print(json.dumps({'selected_strategy':winner,'metrics':metrics,'output':str(output.relative_to(ROOT))},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
