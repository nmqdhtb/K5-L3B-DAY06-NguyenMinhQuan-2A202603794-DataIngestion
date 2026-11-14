"""Edition-specific verse ordinals, independent of inconsistent printed markers."""
import re


def annotate_verse_positions(records):
    ordinal = 0
    anomalies = []
    for record in records:
        start = ordinal + 1
        for line in record['text'].splitlines():
            if not line or line == 'Truyện Kiều (trọn bộ)':
                continue
            marker = re.match(r'^(\d+)\.\s*(.*)$', line)
            if marker:
                printed = int(marker[1])
                if printed != ordinal + 1:
                    anomalies.append({'page': record['page'], 'printed_marker': printed,
                                      'next_extracted_verse_ordinal': ordinal + 1})
                if not marker[2]:
                    continue
            ordinal += 1
        record['metadata'].update(verse_start=start, verse_end=ordinal)
    if ordinal != 3254:
        raise ValueError(f'Expected 3254 verse lines in this edition, got {ordinal}')
    return anomalies
