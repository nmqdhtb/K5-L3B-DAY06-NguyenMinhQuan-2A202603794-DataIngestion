"""Replay frozen queries into a NEW directory; never overwrite original results or reselect."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
os.environ['HF_HOME']=str(ROOT/'starter/.cache/huggingface')
os.environ['HF_HUB_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
import hashlib,json,sys,argparse
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from psycopg import sql
sys.path.insert(0,str(ROOT/'starter'))
from src.embeddings import MyEmbedder
from src.store import PgVectorStore
from src.evaluation import evaluate_query,summarize


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',choices=['dev','test','both'],default='both')
    args=parser.parse_args()
    read=lambda p:json.loads((ROOT/p).read_text())
    selected=read('benchmark/selected_strategy.json')
    for name,digest in selected['frozen_files_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Frozen file changed: {name}')
    config=read('starter/embedding_config.json');load_dotenv(ROOT/'starter/.env')
    signature={k:config[k] for k in ['model_name','revision','pooling','query_document_processing','max_sequence_tokens']}
    store=PgVectorStore(os.environ['DATABASE_URL'],config['dimensions'],signature)
    chunk_config=read('starter/results/chunking/config.json')
    with store.connect() as conn:
        if conn.execute(sql.SQL('SELECT signature FROM {} WHERE id=1').format(store.config)).fetchone()[0]!={**signature,'dimensions':config['dimensions']}:
            raise ValueError('Database model mismatch')
        for strategy in ['A','B','C']:
            expected=[json.loads(x) for x in (ROOT/'starter/results/chunking'/chunk_config['strategies'][strategy]['chunk_file']).read_text().splitlines()]
            rows=conn.execute(sql.SQL('SELECT chunk_id,document_id,source,page,text,metadata FROM {} WHERE strategy=%s').format(store.table),(strategy,)).fetchall()
            actual={r[0]:dict(chunk_id=r[0],document_id=r[1],source=r[2],page=r[3],text=r[4],metadata=r[5]) for r in rows}
            if actual!={c['chunk_id']:c for c in expected}:raise ValueError('Database chunks mismatch')
    embedder=MyEmbedder(config['model_name'],config['revision'],ROOT/config['cache_folder'])
    golds={q['id']:q for q in read('benchmark/questions.json')}
    traces=[]
    for split in (['dev','test'] if args.split=='both' else [args.split]):
        queries=read(f'benchmark/{split}_queries.json')
        vectors=embedder.embed_documents([q['question'] for q in queries])
        for strategy in ['A','B','C']:
            for q,vector in zip(queries,vectors):
                f=q['filter'] if strategy=='C' else None
                hits=store.search(strategy,vector,filters=f)
                traces.append({**evaluate_query(golds[q['id']],hits),'strategy':strategy,'applied_filter':f})
    metrics=summarize(traces)
    execution=read('benchmark/test_execution.json')
    original=[]
    for directory in [selected['dev_run_directory'],execution['test_run_directory']]:
        original+=read(directory+'/metrics.json')
    match=all(all(next(r for r in original if (r['strategy'],r['split'])==(m['strategy'],m['split']))[k]==v for k,v in m.items()) for m in metrics)
    out=ROOT/'starter/results/reproductions'/datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%Y%m%dT%H%M%S%f')
    out.mkdir(parents=True)
    (out/'traces.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces))
    result={'purpose':'reproduction of already observed benchmark; not a new holdout',
            'selected_strategy_unchanged':selected['selected_strategy'],'metrics':metrics,'matches_original_metrics':match,
            'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(out.relative_to(ROOT)),'matches_original_metrics':match,'trace_count':len(traces)},indent=2))
    if not match:raise SystemExit('Reproduction differs; inspect new traces without changing original results')


if __name__=='__main__':main()
