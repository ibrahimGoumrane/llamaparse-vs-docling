# Docling PDF Extraction for RAG

This repository is focused on a Docling-first pipeline for parsing complex PDFs into structured, RAG-ready artifacts.

## What this pipeline does

- Converts PDF to Markdown and JSON
- Extracts text blocks, tables, and figure images
- Optionally enriches figures with VLM descriptions (via local vLLM endpoint)
- Produces chunked output for retrieval workflows

## Requirements

- Python 3.10+
- `uv` installed
- GPU recommended for OCR/performance
- Optional: local vLLM server for picture descriptions

## Setup

```bash
uv sync
```

## Optional: start vLLM for picture descriptions

If you want figure descriptions, start your VLM server first.

```bash
vllm serve "Qwen/Qwen2-VL-2B-Instruct-AWQ" --quantization awq --dtype half --max-model-len 4096 --gpu-memory-utilization 0.90
```

Then keep `USE_VLM = True` in `docling_extract.py`.

If you do not need figure descriptions, set `USE_VLM = False`.

## Run extraction

```bash
uv run python docling_extract.py
```

## Main outputs

Generated under `output/docling/`:

- `full_document.md` (full Markdown)
- `full_document.json` (full document model)
- `texts.json` (text elements)
- `tables.json` (structured tables)
- `figures.json` (figures and optional VLM descriptions)
- `chunks.json` (RAG-ready chunks)
- `table_N_pageX.md` (per-table markdown export)
- `figure_N_pageX.png` (extracted figure images)

## Image payload helper

Use the helper script to decode base64 image payloads from metadata exports:

```bash
uv run python utils/decode_docling_images.py
```

It reads `output/Docling/images.json` and writes files to `output/Docling/decoded_images`.

## Notes and troubleshooting

- If you use API-based picture description, remote services must be enabled in pipeline options.
- If `localhost:8000` times out, either verify the vLLM server is running or set `USE_VLM = False`.
- First run may download OCR model weights.
