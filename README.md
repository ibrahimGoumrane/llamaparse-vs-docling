# PDF Parsing Approaches for RAG: LlamaParse vs Docling

This repository documents two PDF parsing approaches I tested for Retrieval-Augmented Generation (RAG):

- LlamaParse
- Docling

The goal is to share practical results, trade-offs, and the current preferred choice for production usage.

## Context

For RAG pipelines, parsing quality strongly affects downstream retrieval quality.
I evaluated both tools on complex documents containing:

- titles and headings
- rich text formatting
- tables
- charts
- images

## Approach 1: LlamaParse

LlamaParse is a paid API and uses a private model for document parsing.
It integrates directly with LlamaIndex, which is a popular framework for building RAG pipelines.

### Why it stood out

- Very high parsing accuracy on complex PDF structures.
- Strong extraction of tables, charts, and images.
- Produces highly usable Markdown output for downstream indexing.
- Preserves structure well (headings, formatting, links, and semantic organization).
- Smooth integration path for LlamaIndex-based pipelines.

### Pros

- Excellent output quality for production RAG.
- Very good handling of complex layouts.
- Clean, parsable Markdown that is easy to chunk and embed.
- Lower engineering overhead to reach good results quickly.

### Cons

- Paid API, so usage has direct cost.
- Private model and hosted dependency (less local control).

## Approach 2: Docling

Docling is open source and runs locally.
It provides strong document conversion quality and rich pipeline options (OCR, table structure, image export, enrichment).

### What worked well

- Good quality text extraction (titles, headings, and body text).
- Strong table extraction capabilities for an open-source stack.
- Local execution and open ecosystem.
- Flexible pipeline options for advanced workflows.

### Challenges observed

- Setup and runtime are more complex than LlamaParse.
- Image interpretation required additional configuration and helper scripts.
- Better results require stronger hardware, especially for heavier enrichment features.
- In my tests, final structured output quality was good, but still less polished than LlamaParse for full Markdown fidelity.

### Pros

- Open source and locally runnable.
- No mandatory API cost.
- Good extraction quality overall.
- Highly customizable pipeline.

### Cons

- More engineering effort for setup and tuning.
- Hardware-sensitive for full feature usage.
- Image semantics workflow is less straightforward out of the box.

## Side-by-side summary

| Criterion | LlamaParse | Docling |
|---|---|---|
| Cost model | Paid API | Open source / local |
| Integration with LlamaIndex | Native and smooth | Possible, but more setup |
| Complex layout accuracy | Excellent | Good to very good |
| Markdown structure quality | Excellent (rich fidelity) | Good |
| Setup effort | Low | Medium to high |
| Hardware dependency | Lower local burden (hosted API) | Higher for full local features |
| Image understanding path | Strong out of the box | Works, but needs enrichment setup |

## Current recommendation

For my use case, LlamaParse is currently the preferred option.

Main reasons:

- best output fidelity for RAG-ready Markdown
- superior handling of links/formatting/heading hierarchy
- lower operational friction for production-style workflows

Docling remains a strong open-source alternative, especially when local execution and cost control are priorities.

## Docling image payload helper

Docling image metadata can include base64 payloads (for example in image URI fields).
This repository includes a helper script to decode those payloads into previewable image files:

- [utils/decode_docling_images.py](utils/decode_docling_images.py)

### What it does

- Reads [output/Docling/images.json](output/Docling/images.json)
- Accepts both raw base64 and data URI image payloads
- Writes binary image files to [output/Docling/decoded_images](output/Docling/decoded_images)

### Run

uv run python utils/decode_docling_images.py

## Repository outputs

Typical generated outputs in this repo:

- [output/Docling/full_document.md](output/Docling/full_document.md)
- [output/Docling/full_document.json](output/Docling/full_document.json)
- [output/Docling/images.json](output/Docling/images.json)
- [output/Docling/chunks.json](output/Docling/chunks.json)
- [output/Docling/decoded_images](output/Docling/decoded_images)

## Final note

Both tools are capable.
If budget and speed-to-production are key, LlamaParse is easier and stronger in my current tests.
If open-source control is key, Docling is very competitive but needs more setup and infrastructure effort.
