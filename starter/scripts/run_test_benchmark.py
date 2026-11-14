"""Run TEST once after verifying the frozen dev-selected configuration; never reselect."""
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
    if (ROOT / 'benchmark/test_execution.json').exists():
        raise ValueError('Test already executed; preserve the original holdout result')
    selected = read('benchmark/selected_strategy.json')
    for group in ('frozen_files_sha256', 'dev_artifacts_sha256'):
        for name, expected in selected[group].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f'Frozen input/code/dev result changed: {name}')
    selected_hash = hashlib.sha256((ROOT / 'benchmark/selected_strategy.json').read_bytes()).hexdigest()
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
    queries=read('benchmark/test_queries.json')
    golds={q['id']:q for q in read('benchmark/questions.json') if q['split']=='test'}
    if [q['id'] for q in queries] != protocol['split']['test'] or set(golds)!=set(protocol['split']['test']):
        raise ValueError('Test query/gold IDs do not match protocol')
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
    winner=selected['selected_strategy']
    now=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
    output=ROOT/'starter/results/benchmark/test'/now.strftime('%Y%m%dT%H%M%S%f')
    output.mkdir(parents=True,exist_ok=False)
    (output/'traces.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces),encoding='utf-8')
    write(output/'metrics.json',metrics)
    with (output/'metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(metrics[0]),lineterminator='\n');w.writeheader();w.writerows(metrics)
    write(output/'run.json',{'completed_at':now.isoformat(),'split':'test','query_count':len(queries),'trace_count':len(traces),
         'query_embedding_seconds_shared_by_all_strategies':embedding_seconds,'query_embedding_stats':embedder.last_stats,
         'total_seconds_excluding_imports':time.perf_counter()-started,'paid_api_cost_usd':0,
         'model':config,'store':ingestion['database'],'test_run':True})
    execution={'selected_strategy_before_test':winner,'selected_strategy_sha256':selected_hash,
               'completed_at':now.isoformat(),'test_run_directory':str(output.relative_to(ROOT)),
               'frozen_inputs_verified':True,'strategy_reselected':False,
               'test_runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'artifacts_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in output.iterdir() if p.is_file()}}
    write(ROOT/'benchmark/test_execution.json',execution)
    log=ROOT/'artifacts/experiment_log.csv'
    with log.open() as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;entries=list(reader)
    for entry in entries:
        row=next(r for r in metrics if r['strategy']==entry['strategy'])
        entry['test_hit1']=f"{row['hit1_numerator']}/{row['question_count']}"
        entry['test_hit3']=f"{row['hit3_numerator']}/{row['question_count']}"
        entry['notes']=f"Dev và test đã chạy; giữ cấu hình {winner} đã chọn trên dev. Kết quả: {output.relative_to(ROOT)}"
    with log.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(entries)
    print(json.dumps({'selected_strategy':winner,'metrics':metrics,'output':str(output.relative_to(ROOT))},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
