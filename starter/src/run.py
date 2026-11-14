"""Explicit stage dispatcher. Default verifies saved results without network/database access."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    stages={'verify':'verify_submission.py','prepare-corpus':'prepare_corpus.py',
            'build-chunks':'build_chunks.py','prepare-model':'prepare_model.py',
            'ingest':'ingest_vectors.py','dev':'run_dev_benchmark.py',
            'test':'run_test_benchmark.py','reproduce':'reproduce_benchmark.py'}
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=stages,default='verify',nargs='?')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable,str(root/'starter/scripts'/stages[args.stage])],cwd=root,check=True)


if __name__=='__main__':main()
