"""
Docling extraction script for complex PDF documents (RAG chunking + images)
Install: uv add docling
Run:     uv run python docling_extract.py
"""

import json
import shutil
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    smolvlm_picture_description,
)
from docling.chunking import HybridChunker
from docling_core.types.doc.document import PictureItem

# -----------------------------
# 0. Paths
# -----------------------------
PDF_PATH = "RFA2024-pages.pdf"  # <-- change to your PDF
OUTPUT_DIR = Path("output") / "Docling"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# 1. Pipeline configuration
# -----------------------------
pipeline_options = PdfPipelineOptions()

# OCR for scanned documents
pipeline_options.do_ocr = True
pipeline_options.ocr_options.lang = ["fr", "en"]  # adjust languages

# Layout & structure
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True

# Images
pipeline_options.generate_picture_images = True
pipeline_options.images_scale = 3.0  # high-res

# Native Docling image enrichment
pipeline_options.do_picture_description = True
pipeline_options.picture_description_options = smolvlm_picture_description
pipeline_options.picture_description_options.prompt = (
    "Describe this figure for retrieval in 2-3 factual sentences."
)

# On Windows, picture classification may trigger torch inductor and require MSVC cl.exe.
has_msvc_cl = shutil.which("cl") is not None
pipeline_options.do_picture_classification = has_msvc_cl
if not has_msvc_cl:
    print(
        "Warning: MSVC compiler (cl.exe) not found. "
        "Disabling do_picture_classification to avoid torch inductor failure."
    )

# -----------------------------
# 2. Document conversion
# -----------------------------
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

print("Converting document...")
result = converter.convert(PDF_PATH)
doc = result.document

# -----------------------------
# 3. Export raw Markdown
# -----------------------------
md = doc.export_to_markdown()
(OUTPUT_DIR / "full_document.md").write_text(md, encoding="utf-8")
print(f"Markdown exported → {OUTPUT_DIR}/full_document.md")

# -----------------------------
# 4. Export raw JSON
# -----------------------------
doc_json = doc.export_to_dict()
(OUTPUT_DIR / "full_document.json").write_text(
    json.dumps(doc_json, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"JSON exported → {OUTPUT_DIR}/full_document.json")

# -----------------------------
# 5. Extract images
# -----------------------------
images = []
picture_index = {}
for element, _level in doc.iterate_items(traverse_pictures=True):
    if isinstance(element, PictureItem):
        image_uri = getattr(getattr(element, "image", None), "uri", None)
        page_no = element.prov[0].page_no if element.prov else None
        caption_text = element.caption_text(doc=doc)
        description_text = None
        description_source = None
        if element.meta is not None and element.meta.description is not None:
            description_text = element.meta.description.text
            description_source = element.meta.description.created_by

        item = {
            "id": str(element.self_ref),
            "path": str(image_uri) if image_uri is not None else None,
            "page": page_no,
            "caption": caption_text,
            "description": description_text,
            "description_model": description_source,
        }
        images.append(item)
        picture_index[item["id"]] = item

(OUTPUT_DIR / "images.json").write_text(
    json.dumps(images, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Images metadata exported → {OUTPUT_DIR}/images.json")

# -----------------------------
# 6. Chunking
# -----------------------------
chunker = HybridChunker(
    tokenizer="BAAI/bge-base-en-v1.5",  # stronger embeddings
    max_tokens=400,
    merge_peers=True,
)

chunks_raw = list(chunker.chunk(doc))
chunks_output = []

for i, chunk in enumerate(chunks_raw):
    # Link enriched image metadata in this chunk
    related_images = []
    related_image_descriptions = []
    for item in chunk.meta.doc_items:
        if isinstance(item, PictureItem):
            picture_id = str(item.self_ref)
            picture_info = picture_index.get(picture_id)
            if picture_info is not None:
                related_images.append(picture_info)
                if picture_info.get("description"):
                    related_image_descriptions.append(picture_info["description"])

    related_images = list({img["id"]: img for img in related_images}.values())
    related_image_descriptions = list(dict.fromkeys(related_image_descriptions))

    # Optional: LLM-based enrichment placeholder
    enriched_text = chunk.text
    # enriched_text = llm_enrich(chunk.text)  # define your local LLM enrichment function

    chunks_output.append({
        "chunk_id": f"chunk_{i+1:04d}",
        "content": enriched_text,
        "images": related_images,
        "image_descriptions": related_image_descriptions,
    })

(OUTPUT_DIR / "chunks.json").write_text(
    json.dumps(chunks_output, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Chunks exported → {OUTPUT_DIR}/chunks.json")
print(f"\nTotal chunks: {len(chunks_output)}")

# -----------------------------
# 7. Optional: Image captions (placeholder)
# -----------------------------
# for img in images:
#     img["description"] = vision_model.describe(img["path"])
# Save updated image metadata if you implement this
# (OUTPUT_DIR / "images_captions.json").write_text(json.dumps(images, ensure_ascii=False, indent=2), encoding="utf-8")