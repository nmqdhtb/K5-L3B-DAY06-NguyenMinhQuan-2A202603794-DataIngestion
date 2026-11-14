"""Prepare source-checked audit sheets; never assign human scores or confirmations."""
import hashlib
import json
import re
import sys
from pathlib import Path
from pypdf import PdfReader
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'starter'))
from src.ingestion import normalize_text


def read(path):return json.loads((ROOT/path).read_text())


def main():
    execution=read('benchmark/test_execution.json')
    for path,digest in execution['artifacts_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('Test artifacts changed')
    traces=[json.loads(line) for line in (ROOT/execution['test_run_directory']/'traces.jsonl').read_text().splitlines()]
    source=read('data/manifest.json')['sources'][0]
    pdf=ROOT/source['local_path']
    if hashlib.sha256(pdf.read_bytes()).hexdigest()!=source['snapshot_or_version']['sha256']:
        raise ValueError('PDF changed')
    reader=PdfReader(pdf)
    pages={n:normalize_text(reader.pages[n-1].extract_text()).replace('ƣ','ư') for n in source['included_page_ids']}
    ordinal=0; ranges={}
    for n,text in sorted(pages.items()):
        start=ordinal+1
        for line in text.splitlines():
            if not line or line=='Truyện Kiều (trọn bộ)':continue
            marker=re.match(r'^\d+\.\s*(.*)$',line)
            if marker and not marker[1]:continue
            ordinal+=1
        ranges[n]=(start,ordinal)
    metadata=[]
    for trace in traces:
        for hit in trace['hits']:
            m=hit['metadata'];page=hit['page'];text=pages.get(page,'')
            required=['verse_start','verse_end','char_start','char_end']
            complete=all(k in m for k in required) and all(k in hit for k in ['document_id','source','page'])
            offsets=complete and 0<=m['char_start']<m['char_end']<=len(text)
            checks={'required_fields':complete,'source_matches_manifest':hit['source']==source['source_path_or_url'],
                    'document_id_matches_manifest':hit['document_id']==source['source_id'],
                    'physical_page_exists':page in pages,
                    'chunk_matches_reextracted_pdf':bool(offsets and text[m['char_start']:m['char_end']]==hit['text']),
                    'verse_range_matches_pdf_derived_ordinals':complete and ranges.get(page)==(m['verse_start'],m['verse_end'])}
            metadata.append({'strategy':trace['strategy'],'question_id':trace['question_id'],'rank':hit['rank'],
                             'chunk_id':hit['chunk_id'],'source':hit['source'],'page':page,'metadata':m,
                             'checks':checks,'automatic_complete_and_correct':all(checks.values()),
                             'student_complete_and_correct':None,'student_notes':None,'reviewer':None})
    output=ROOT/'starter/results/audit'
    output.mkdir(parents=True,exist_ok=True)
    sheets={'metadata_review.json':metadata,
            'grounding_review.json':[{'strategy':t['strategy'],'question_id':t['question_id'],'question':t['question'],
                'expected_answer':t['expected_answer'],'hits':t['hits'],'score':None,'reason':None,'reviewer':None} for t in traces],
            'coherence_review.json':read('starter/results/chunking/coherence_review.json')}
    for name,data in sheets.items():
        path=output/name
        if path.exists():raise ValueError(f'{name} exists; do not overwrite annotations')
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'metadata_records':len(metadata),'automatic_correct':sum(x['automatic_complete_and_correct'] for x in metadata),
                      'grounding_samples':len(traces),'coherence_samples':len(sheets['coherence_review.json']),
                      'human_labels':'not assigned'},indent=2))


if __name__=='__main__':main()
