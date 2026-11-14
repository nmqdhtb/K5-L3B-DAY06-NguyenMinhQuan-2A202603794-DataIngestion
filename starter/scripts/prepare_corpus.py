"""Prepare the supplied Kieu edition. Run from any working directory."""
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pypdf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "starter"))
from src.ingestion import load_pdf, normalize_text
from src.corpus_metadata import annotate_verse_positions


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    manifest_path = ROOT / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records, errors, summaries = [], [], []
    for entry in manifest["sources"]:
        path = ROOT / entry["local_path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["snapshot_or_version"]["sha256"]:
            raise ValueError("PDF changed; review manifest and normalization before continuing")
        pages = load_pdf(path, entry["source_id"], entry["source_path_or_url"])
        selected = entry["included_page_ids"]
        if len(selected) != len(set(selected)) or not set(selected) <= set(range(1, len(pages) + 1)):
            raise ValueError("Invalid or duplicate included page IDs")
        counts, repairs = {}, 0
        for page in pages:
            status = page.metadata["extraction_status"]
            if status != "ok":
                errors.append({"document_id": page.document_id, "page": page.page, **page.metadata})
            if page.page not in selected:
                continue
            if status != "ok":
                raise ValueError(f"Included page {page.page} could not be extracted")
            # Verified font extraction defect in this exact PDF, not a generic Vietnamese rule.
            replacements = page.text.count("ƣ")
            page.text = normalize_text(page.text.replace("ƣ", "ư"))
            repairs += replacements
            counts[str(page.page)] = len(page.text)
            page.metadata.update(normalization_replacements=replacements,
                                 normalized_character_count=len(page.text))
            records.append(asdict(page))
        entry["physical_page_count"] = len(pages)
        entry["content_page_count"] = len(counts)
        entry["normalized_character_counts_by_page"] = counts
        entry["normalization_status"] = "Đã chuẩn hóa NFC, khoảng trắng, giữ dòng/đoạn và số câu; sửa ƣ → ư riêng cho snapshot PDF này."
        entry["status"] = "Đã xuất corpus chuẩn hóa; chưa chạy embedding. Quyền bản PDF chưa được xác minh độc lập."
        summaries.append({"source_id": entry["source_id"], "physical_pages": len(pages),
                          "included_pages": len(counts), "normalized_characters": sum(counts.values()),
                          "replacements_u": repairs, "sha256": digest})
    if len(records) < 30:
        raise ValueError("Fewer than 30 selected nonempty pages")
    if len(manifest['sources']) != 1 or manifest['sources'][0]['source_id'] != 'truyen-kieu-nguyen-du':
        raise ValueError('Verse annotation is specific to the supplied Kieu edition')
    anomalies = annotate_verse_positions(records)
    output = ROOT / "data/processed"
    output.mkdir(parents=True, exist_ok=True)
    results = ROOT / "starter/results"
    results.mkdir(parents=True, exist_ok=True)
    (output / "pages.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    (output / "pages.txt").write_text("\n\n".join(f"=== PDF PAGE {r['page']} | {r['document_id']} ===\n{r['text']}" for r in records) + "\n", encoding="utf-8")
    (results / "ingestion_errors.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in errors), encoding="utf-8")
    write_json(results / "corpus_validation.json", {
        "checked_at": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
        "python_version": sys.version.split()[0], "pypdf_version": pypdf.__version__,
        "sources": summaries, "extraction_errors_or_empty_pages": len(errors),
        "verse_numbering_anomalies": anomalies,
        "scope": "Extraction checks only; not proof of licensing or manual review of every page",
    })
    write_json(manifest_path, manifest)
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
