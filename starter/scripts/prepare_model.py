"""Download the public model once, pin revision, then use it offline."""
import os
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[2]
os.environ['HF_HOME'] = str(ROOT / 'starter/.cache/huggingface')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
sys.path.insert(0, str(ROOT / 'starter'))
from huggingface_hub import HfApi, snapshot_download


def main():
    path = ROOT / 'starter/embedding_config.json'
    if path.exists():
        config = json.loads(path.read_text())
    else:
        name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        config = {'model_name': name, 'revision': HfApi().model_info(name).sha,
                  'device': 'cpu', 'dimensions': 384,
                  'pooling': 'recursive whitespace segments within token limit; token-count-weighted mean of L2-normalized segment vectors, then L2 normalize',
                  'query_document_processing': 'identical; no prefix',
                  'cache_folder': 'starter/.cache/huggingface/hub'}
    snapshot_download(config['model_name'], revision=config['revision'],
                      cache_dir=str(ROOT / config['cache_folder']),
                      allow_patterns=['*.json', '*.txt', '*.model', 'model.safetensors'],
                      ignore_patterns=['onnx/*', 'openvino/*', 'onnx*', 'openvino*'])
    from src.embeddings import MyEmbedder
    embedder = MyEmbedder(config['model_name'], config['revision'], ROOT / config['cache_folder'])
    if embedder.dimensions != config['dimensions']:
        raise ValueError('Unexpected model dimensions')
    config['max_sequence_tokens'] = embedder.token_limit
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
