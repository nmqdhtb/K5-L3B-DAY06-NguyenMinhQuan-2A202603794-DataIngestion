"""Page-local chunking with stable IDs and exact source character offsets."""
from copy import deepcopy
import hashlib
import json
import re
from .models import Chunk, DocumentPage


def _chunk(page: DocumentPage, start: int, end: int, config: dict) -> Chunk:
    text = page.text[start:end]
    identity = [page.document_id, page.source, page.page, config,
                hashlib.sha256(page.text.encode()).hexdigest(), start, end]
    chunk_id = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    metadata = deepcopy(page.metadata)
    metadata.update(char_start=start, char_end=end, chunking=config.copy())
    return Chunk(chunk_id, page.document_id, page.source, page.page, text, metadata)


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Overlapping character windows; never cross physical page boundaries."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Require size > 0 and 0 <= overlap < size')
    if not page.text.strip():
        return []
    chunks = []
    start = 0
    while start < len(page.text):
        end = min(start + size, len(page.text))
        chunks.append(_chunk(page, start, end, {'method': 'fixed', 'size': size, 'overlap': overlap}))
        if end == len(page.text):
            break
        start = end - overlap
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Pack blank-line-separated blocks, splitting long blocks at verse-line ends.

    Keep every source character, including paragraph separators. A single line
    longer than max_size is hard-split as a last resort. No added overlap.
    """
    if max_size <= 0:
        raise ValueError('max_size must be positive')
    if not page.text.strip():
        return []
    boundaries = [0] + [m.end() for m in re.finditer(r'\n\n+', page.text)]
    if boundaries[-1] != len(page.text):
        boundaries.append(len(page.text))
    pieces = []
    for start, end in zip(boundaries, boundaries[1:]):
        while end - start > max_size:
            cut = page.text.rfind('\n', start, start + max_size)
            cut = cut + 1 if cut >= start else start + max_size
            pieces.append((start, cut))
            start = cut
        if end > start:
            pieces.append((start, end))
    spans = []
    for start, end in pieces:
        if spans and end - spans[-1][0] <= max_size:
            spans[-1] = (spans[-1][0], end)
        else:
            spans.append((start, end))
    return [_chunk(page, start, end, {'method': 'paragraph', 'max_size': max_size, 'overlap': 0})
            for start, end in spans]
