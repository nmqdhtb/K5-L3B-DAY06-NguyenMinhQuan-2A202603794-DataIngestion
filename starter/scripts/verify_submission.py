"""Offline verification of frozen inputs, metrics and confirmed audit labels."""
import hashlib,json,sys,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'starter'))
from src.evaluation import summarize


def main():
    read=lambda p:json.loads((ROOT/p).read_text())
    selected=read('benchmark/selected_strategy.json');test=read('benchmark/test_execution.json')
    for group in [selected['frozen_files_sha256'],selected['dev_artifacts_sha256'],test['artifacts_sha256']]:
        for path,digest in group.items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError(f'Hash mismatch: {path}')
    if hashlib.sha256((ROOT/'benchmark/selected_strategy.json').read_bytes()).hexdigest()!=test['selected_strategy_sha256']:
        raise ValueError('Selection record changed after test')
    if hashlib.sha256((ROOT/'starter/scripts/run_test_benchmark.py').read_bytes()).hexdigest()!=test['test_runner_sha256']:
        raise ValueError('Original test runner changed')
    trace_count=hit_count=0
    for split,directory,n in [('dev',selected['dev_run_directory'],15),('test',test['test_run_directory'],5)]:
        traces=[json.loads(x) for x in (ROOT/directory/'traces.jsonl').read_text().splitlines()]
        metrics=read(directory+'/metrics.json')
        if len(traces)!=3*n or {t['split'] for t in traces}!={split}:raise ValueError('Wrong trace count/split')
        for computed,saved in zip(summarize(traces),metrics,strict=True):
            if not all(saved[k]==v for k,v in computed.items()):raise ValueError('Metric mismatch')
        trace_count+=len(traces);hit_count+=sum(len(t['hits']) for t in traces)
    audit=read('starter/results/audit/summary.json')
    for filename,expected in [('coherence_review.json',30),('grounding_review.json',15),('metadata_review.json',45)]:
        rows=read('starter/results/audit/'+filename)
        if len(rows)!=expected or not all(r['student_review_status']=='confirmed' and r['reviewer'] for r in rows):
            raise ValueError('Incomplete audit confirmations')
        for strategy in ['A','B','C']:
            subset=[r for r in rows if r['strategy']==strategy];summary=audit['strategies'][strategy]
            if filename=='metadata_review.json':
                if sum(r['student_complete_and_correct'] for r in subset)!=summary['student_confirmed_metadata_correct']:raise ValueError('Metadata summary mismatch')
            else:
                key='confirmed_'+('coherence' if filename.startswith('coherence') else 'grounding')+'_mean_out_of_2'
                if any(r['score'] not in [0,1,2] or not r['reason'] for r in subset):raise ValueError('Invalid audit score')
                if sum(r['score'] for r in subset)/len(subset)!=summary[key]:raise ValueError('Audit mean mismatch')
    required=['STUDENT.md','README.md','report/individual/2A202603794_NguyenMinhQuan.md','data/manifest.json','artifacts/experiment_log.csv']
    for path in required:
        if not (ROOT/path).is_file():raise ValueError(f'Missing submission file: {path}')
    # Best-effort high-confidence pattern scan; never print matching secret values.
    names=set(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines())
    tracked=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines())
    forbidden=[n for n in tracked if Path(n).name=='.env' or '/.venv/' in '/'+n or '/.cache/' in '/'+n]
    findings=[]
    patterns=[r'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}',r'\bgh[pousr]_[A-Za-z0-9]{30,}',r'\bhf_[A-Za-z0-9]{30,}',r'^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----$']
    for name in names:
        path=ROOT/name
        if not path.is_file() or path.suffix in ['.pdf','.png','.pyc']:continue
        try:text=path.read_text()
        except (UnicodeError,OSError):continue
        if any(re.search(p,text,re.MULTILINE) for p in patterns):findings.append(name)
    if forbidden or findings:raise ValueError(f'Sensitive-file/pattern review required: {sorted(set(forbidden+findings))}')
    result={'technical_checks':'passed','original_traces':trace_count,'retrieved_chunks':hit_count,
            'confirmed_coherence':30,'confirmed_grounding':15,'confirmed_metadata':45,
            'selected_strategy':selected['selected_strategy'],'high_confidence_secret_pattern_findings':0,
            'scan_scope':'Git-tracked and nonignored text; heuristic, not a guarantee; local-only lab password intentionally allowed',
            'pdf_permission_basis': 'Student confirmation recorded in data/manifest.json',
            'remaining_submission_items': ([] if read('data/manifest.json')['sources'][0]['license_or_permission'].get('sharing_permission_confirmed_by_student') else ['PDF edition permission/re-distribution verification']) + ['Final commit and push','Grader repository access and submission link delivery']}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
