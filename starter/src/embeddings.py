"""Real local embeddings with explicit handling of texts exceeding model limits."""
from pathlib import Path
from typing import Protocol
import numpy as np
import torch
from sentence_transformers import SentenceTransformer


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, question: str) -> list[float]: ...


class MyEmbedder:
    def __init__(self, model_name: str, revision: str, cache_folder: Path,
                 local_files_only: bool = True) -> None:
        self.model_name = model_name
        self.revision = revision
        torch.set_num_threads(4)
        self.model = SentenceTransformer(model_name, revision=revision, device='cpu',
                                         cache_folder=str(cache_folder),
                                         local_files_only=local_files_only,
                                         trust_remote_code=False)
        self.dimensions = self.model.get_embedding_dimension()
        self.token_limit = self.model.max_seq_length
        self.model.eval()
        self.last_stats = {}

    def _segments(self, text: str) -> list[str]:
        """Recursively split long text at whitespace; never silently truncate tokens."""
        if not text.strip():
            raise ValueError('Cannot embed empty text')
        tokenizer = self.model.tokenizer
        if len(tokenizer.encode(text, add_special_tokens=True, truncation=False, verbose=False)) <= self.token_limit:
            return [text]
        middle = len(text) // 2
        whitespace = [i for i, c in enumerate(text) if c.isspace() and text[:i].strip() and text[i:].strip()]
        cut = min(whitespace, key=lambda i: abs(i - middle)) if whitespace else middle
        if cut <= 0 or cut >= len(text):
            raise ValueError('Cannot split text to fit model token limit')
        return self._segments(text[:cut]) + self._segments(text[cut:])

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        groups = [self._segments(t) for t in texts]
        flat = [segment for group in groups for segment in group]
        lengths = [len(self.model.tokenizer.encode(t, add_special_tokens=False, truncation=False)) for t in flat]
        vectors = self.model.encode(flat, batch_size=16, normalize_embeddings=True,
                                    convert_to_numpy=True, show_progress_bar=True)
        output, offset = [], 0
        for group in groups:
            stop = offset + len(group)
            vector = np.average(vectors[offset:stop], axis=0, weights=lengths[offset:stop])
            norm = np.linalg.norm(vector)
            if not np.isfinite(vector).all() or norm <= 0:
                raise ValueError('Invalid embedding from model')
            output.append((vector / norm).astype(np.float32).tolist())
            offset = stop
        self.last_stats = {'texts': len(texts), 'segments': len(flat),
                           'texts_split_for_token_limit': sum(len(g) > 1 for g in groups),
                           'content_tokens_encoded': sum(lengths), 'max_content_tokens': max(lengths)}
        return output

    def embed_query(self, question: str) -> list[float]:
        return self.embed_documents([question])[0]
