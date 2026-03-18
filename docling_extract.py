"""
Docling extraction script for complex PDF documents (RAG chunking)

Setup:
    1. Replace your pyproject.toml with the one provided
    2. Run: uv sync
    3. Start vLLM in WSL first (for picture description):
           vllm serve "Qwen/Qwen2-VL-2B-Instruct-AWQ" --quantization awq --dtype half --max-model-len 4096 --gpu-memory-utilization 0.90
    4. Run: uv run python docling_extract.py
"""

import os
import json
import shutil
import platform
from pathlib import Path

# ── Windows: disable symlinks before any HF import ───────────────────────────
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HUGGINGFACE_HUB_VERBOSITY"] = "error"

if platform.system() == "Windows":
    try:
        import huggingface_hub.file_download as _hf
        def _no_symlink(src, dst, **kw):
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
        _hf._create_symlink = _no_symlink
    except Exception:
        pass

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
)
from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
from docling.chunking import HybridChunker

# ── Config ────────────────────────────────────────────────────────────────────
PDF_PATH   = "RFA2024-pages.pdf"
OUTPUT_DIR = Path("output") / "docling"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Set to False if vLLM is not running
USE_VLM    = True
VLLM_URL   = "http://localhost:8000/v1/chat/completions"
VLLM_MODEL = "Qwen/Qwen2-VL-2B-Instruct-AWQ"


# ── 1. Pipeline options ───────────────────────────────────────────────────────
pipeline_options = PdfPipelineOptions()

pipeline_options.accelerator_options = AcceleratorOptions(
    device=AcceleratorDevice.CUDA
)

pipeline_options.do_ocr = True
pipeline_options.ocr_options.lang = ["fr", "en"]

pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True

pipeline_options.generate_picture_images = True
pipeline_options.images_scale = 2.0

# Picture description via vLLM API — no local model loading, no quantization issues
pipeline_options.do_picture_description = USE_VLM
pipeline_options.enable_remote_services = USE_VLM
if USE_VLM:
    pipeline_options.picture_description_options = PictureDescriptionApiOptions(
        url=VLLM_URL,
        params=dict(
            model=VLLM_MODEL,
            max_tokens=200,
            temperature=0.0,
        ),
        prompt=(
            "You are analyzing a figure from a French financial report. "
            "Describe what this figure shows in 2-3 factual sentences. "
            "If it is a chart, list all data points with their labels and values. "
            "If it is a table, summarize the key numbers."
        ),
    )

# Disable picture classification on Windows (requires MSVC cl.exe)
pipeline_options.do_picture_classification = False


# ── 2. Convert ────────────────────────────────────────────────────────────────
converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)

print("Converting document...")
result = converter.convert(PDF_PATH)
doc = result.document
print("Done.")


# ── 3. Markdown export ────────────────────────────────────────────────────────
md = doc.export_to_markdown()
(OUTPUT_DIR / "full_document.md").write_text(md, encoding="utf-8")
print(f"Markdown  -> {OUTPUT_DIR}/full_document.md")


# ── 4. JSON export ────────────────────────────────────────────────────────────
(OUTPUT_DIR / "full_document.json").write_text(
    json.dumps(doc.export_to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"JSON      -> {OUTPUT_DIR}/full_document.json")


# ── 5. Extract elements ───────────────────────────────────────────────────────
try:
    from docling.datamodel.document import TextItem, SectionHeaderItem, ListItem, TableItem, PictureItem
except ImportError:
    from docling_core.types.doc.document import TextItem, SectionHeaderItem, ListItem, TableItem, PictureItem

texts, tables, figures = [], [], []

for item, level in doc.iterate_items():

    if isinstance(item, (TextItem, SectionHeaderItem, ListItem)):
        texts.append({
            "type"  : type(item).__name__,
            "label" : str(item.label),
            "page"  : item.prov[0].page_no if item.prov else None,
            "text"  : item.text,
        })

    elif isinstance(item, TableItem):
        page   = item.prov[0].page_no if item.prov else None
        tbl_md = item.export_to_markdown(doc=doc)
        idx    = len(tables) + 1
        (OUTPUT_DIR / f"table_{idx}_page{page}.md").write_text(tbl_md, encoding="utf-8")
        try:
            df   = item.export_to_dataframe(doc=doc)
            rows = df.values.tolist()
            cols = list(df.columns)
        except Exception:
            rows, cols = [], []
        tables.append({
            "table_id" : f"tbl_{idx:03d}",
            "page"     : page,
            "markdown" : tbl_md,
            "columns"  : cols,
            "rows"     : rows,
        })
        print(f"  Table {idx} (page {page}) -> {len(rows)} rows")

    elif isinstance(item, PictureItem):
        page = item.prov[0].page_no if item.prov else None
        idx  = len(figures) + 1
        img_path = OUTPUT_DIR / f"figure_{idx}_page{page}.png"
        if item.image and item.image.pil_image:
            item.image.pil_image.save(img_path)

        caption     = ""
        description = ""
        try:
            caption = item.caption_text(doc) or ""
        except Exception:
            pass
        try:
            if item.meta and item.meta.description:
                description = item.meta.description.text or ""
        except Exception:
            pass

        figures.append({
            "figure_id"   : f"fig_{idx:03d}",
            "page"        : page,
            "caption"     : caption,
            "description" : description,
            "image_path"  : str(img_path),
        })
        print(f"  Figure {idx} (page {page}) -> {img_path}")
        if description:
            print(f"    VLM: {description[:100]}...")

(OUTPUT_DIR / "texts.json").write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8")
(OUTPUT_DIR / "tables.json").write_text(json.dumps(tables, ensure_ascii=False, indent=2), encoding="utf-8")
(OUTPUT_DIR / "figures.json").write_text(json.dumps(figures, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 6. Chunking ───────────────────────────────────────────────────────────────
chunker = HybridChunker(
    tokenizer="BAAI/bge-small-en-v1.5",
    max_tokens=512,
    merge_peers=True,
)

chunks_raw    = list(chunker.chunk(doc))
chunks_output = []


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return getattr(value, "text", str(value))


for i, chunk in enumerate(chunks_raw):
    meta = getattr(chunk, "meta", None)
    headings_raw = getattr(meta, "headings", None) if meta else None
    doc_items = getattr(meta, "doc_items", None) if meta else None

    headings = [_to_text(h) for h in headings_raw] if headings_raw else []
    el_types = list({str(getattr(ref, "label", "")) for ref in doc_items if getattr(ref, "label", None)}) if doc_items else []
    page     = None
    if doc_items and getattr(doc_items[0], "prov", None):
        page = doc_items[0].prov[0].page_no

    chunks_output.append({
        "chunk_id"      : f"chunk_{i+1:04d}",
        "heading_path"  : headings,
        "element_types" : el_types,
        "page"          : page,
        "content"       : chunk.text,
        "token_count"   : len(chunk.text.split()),
    })

(OUTPUT_DIR / "chunks.json").write_text(
    json.dumps(chunks_output, ensure_ascii=False, indent=2), encoding="utf-8"
)


# ── 7. Summary ────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("DOCLING EXTRACTION SUMMARY")
print("="*50)
print(f"  Text elements : {len(texts)}")
print(f"  Tables        : {len(tables)}")
print(f"  Figures       : {len(figures)}")
print(f"  Chunks        : {len(chunks_output)}")
print(f"\nOutput in ./{OUTPUT_DIR}/")
print("  full_document.md   - full markdown")
print("  full_document.json - doc model with bounding boxes")
print("  texts.json         - all text elements")
print("  tables.json        - structured tables")
print("  figures.json       - figures + VLM descriptions")
print("  chunks.json        - RAG-ready chunks")
print("  table_N_pageX.md   - individual tables")
print("  figure_N_pageX.png - extracted figure images")