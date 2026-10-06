# Feature: rag-clase

**Status:** in progress
**Owner:** el Gentleman (orchestrator)
**Created:** 2026-10-06
**Feature branch:** main

## Objective

Build reproducible teaching material for a UADEO class on Retrieval-Augmented Generation
in n8n, delivered as **two separate workflows** plus a runnable local environment:

1. **Workflow 01 — Ingestion:** a student uploads a PDF through a form, the text is
   extracted, chunked, embedded, and written to a shared pgvector collection.
2. **Workflow 02 — Query:** a chat agent answers questions about that collection,
   grounded in retrieved chunks and citing sources.

Delivery mode: **teacher live demo + student hands-on practice** (deliverable for students).

## Frozen decisions

| Decision | Value | Rationale |
| --- | --- | --- |
| Vector store | **pgvector** on a dedicated Postgres container | Two workflows require a durable store shared across workflows; n8n's In-Memory store is volatile (cleared on restart, evictable under memory pressure) |
| Chat / generation model | **DeepSeek** (`DeepSeek Chat Model`, native node) | Confirmed present in the teacher's image as `LmChatDeepSeek`; cheap; OpenAI-compatible API |
| Embeddings | **OpenAI `text-embedding-3-small`** (1536 dims) | DeepSeek exposes no embeddings endpoint; verified in docs, n8n community, and the teacher's own image (no `EmbeddingsDeepSeek` node exists) |
| n8n version targeted | **2.38.6** (n8n 2.x) | Teacher's running image; node architecture differs from the n8n 1.x tutorials that dominate the web |
| Language split | ODD tracking in English; student-facing docs in Spanish | Default artifact language is English, overridden for the course audience |

## Non-goals

- No OCR pipeline for scanned PDFs (one scanned PDF is included deliberately as a
  case study of silent retrieval failure).
- No reranking, hybrid search, or evaluation harness in the base class.
- No production hardening: no auth on the form, no rate limiting, no backups.
- Does not modify the teacher's live n8n compose at
  `/Users/alfonsoduarte/Documents/desarrollo/docker/n8n/docker-compose.yml`.

## Environment facts (verified, not assumed)

| Item | Value |
| --- | --- |
| Teacher's n8n | `n8nio/n8n:2.38.6` container `n8n-n8n-1`, bound to `127.0.0.1:5678` |
| Teacher's n8n internal DB | `n8n-postgres-1` (`postgres:16-alpine`) — workflow/credential storage only, never the vector store |
| Host port 5432 | Already taken by `infra-postgres-1` |
| pgvector image | `vxcontrol/pgvector:latest` already cached locally |
| Teacher toolchain | Docker 29.4.0, Compose v5.1.2, Python 3.9.6 + reportlab, pandoc, git identity configured |
| Students | Environment unverified — material must work both standalone and attached to an existing n8n |

## Tasks

### T1 — Recon: extract the real node schema from n8n 2.38.6
**Acceptance:** For each node used by either workflow, the exact node type string,
`typeVersion`, connector types, and the parameter names/values needed to author a
working workflow JSON by hand. Resolve the n8n 2.x PGVector "Collection" vs legacy
`tableName` question explicitly.
**Status:** done

**Findings (extracted from the running 2.38.6 container, not from docs):**

| Node | type string | versions | credential |
| --- | --- | --- | --- |
| Form Trigger | `n8n-nodes-base.formTrigger` | 2 … 2.6 | — |
| Extract from File | `n8n-nodes-base.extractFromFile` | 1, 1.1 | — |
| Default Data Loader | `@n8n/n8n-nodes-langchain.documentDefaultDataLoader` | 1, **1.1** (default) | — |
| Recursive Character Text Splitter | `…textSplitterRecursiveCharacterTextSplitter` | 1 | — |
| Embeddings OpenAI | `…embeddingsOpenAi` | 1 … 1.2 | `openAiApi` |
| PGVector | `…vectorStorePGVector` | 1 … 1.3 | `postgres` |
| Chat Trigger | `…chatTrigger` | 1 … **1.4** (default) | — |
| AI Agent | `…agent` | 1 … 3.1 | — |
| DeepSeek Chat Model | `…lmChatDeepSeek` | 1 | `deepSeekApi` |
| Simple Memory | `…memoryBufferWindow` | 1 … 1.4 | — |
| Vector Store QA Tool | `…toolVectorStore` | 1, 1.1 | — |

- **Correction to an earlier assumption.** PGVector does *not* require the new Collection
  abstraction: `useCollection` is a field inside `options.collection` with default
  **`false`**, so the node operates in classic `tableName` mode (default `n8n_vectors`).
  `collectionName` / `collectionTableName` are only rendered when `useCollection: true`.
  The names seen earlier came from the LangChain store class, not from the node UI.
- **Default PGVector column names** (`options.columnNames`): `id`, `embedding`, `text`,
  `metadata`. This fixes what the table must look like, but see T2's table decision.
- **PGVector modes**: `load`, `insert`, `retrieve`, `retrieve-as-tool`. In
  `retrieve-as-tool` the node exposes `ai_embedding` in and `ai_tool` out, which enables
  the modern pattern of wiring the vector store straight into the Agent's tool port —
  one model, no separate QA-chain tool, no second model connection.
- **Connector wiring for insert mode**: inputs are `ai_embedding` + `main` +
  `ai_document`, output is `main`. So the main flow passes *through* the vector store
  node while the loader and embedder hang off AI ports.
- **`ToolVectorStore` needs its own model** (`ai_vectorStore` + `ai_languageModel` in),
  which is why `retrieve-as-tool` is the better teaching path.
- **In-Memory Vector Store is confirmed volatile** by its own description:
  "…restarts. Data may also be cleared if available memory gets low, and is accessible
  to all users of this instance." This is the citable justification for the external
  store.

**Method note:** the delegated explorer reported honestly that it had no shell access and
returned nothing fabricated. Recon was completed inline with a purpose-built schema
digester (`require()` + instantiate + walk `description.properties`), keeping output
bounded instead of dumping full schemas.

### T2 — Reproducible environment skeleton
**Acceptance:** `clase-rag/docker/docker-compose.yml` brings up n8n + pgvector from
scratch; `docker-compose.vectorstore.yml` attaches a pgvector container to an existing
`n8n_default` network without touching the teacher's compose; `db/init.sql` creates the
`vector` extension and the documents table. Teacher's live compose is byte-identical.
**Status:** pending

### T3 — Workflow 01: PDF ingestion
**Acceptance:** `workflows/01-ingesta-pdf.json` imports cleanly into 2.38.6, extracts
text from a PDF, writes chunks + metadata (`file_name`, `doc_id`, `uploaded_at`) into
the pgvector collection, and is idempotent on re-upload of the same document.
**Status:** pending

### T4 — Workflow 02: grounded Q&A
**Acceptance:** `workflows/02-consulta-rag.json` imports cleanly, answers questions over
the collection indexed by Workflow 01, cites the source file, and refuses to answer when
the context does not contain the answer.
**Status:** pending

### T5 — End-to-end verification
**Acceptance:** Observed evidence that the stack runs, a test PDF is indexed, rows exist
in the pgvector table, and a query returns an answer grounded in the document. Evidence
recorded here; failure modes reported honestly.
**Status:** pending

### T6 — Test dataset
**Acceptance:** Three PDFs: plain text, one with a table, and one scanned (no text layer).
The scanned one must be documented as the deliberate failure case.
**Status:** pending

### T7 — Teacher and student documentation
**Acceptance:** `README.md` with per-block timing for the demo+practice format,
`docs/guia-alumno.md`, `docs/conceptos-rag.md`, `docs/troubleshooting.md`. Spanish.
**Status:** pending

### T8 — Closure
**Acceptance:** Clean tree, evidence summarized, `mem_session_summary` written,
remaining gaps stated.
**Status:** pending

## Evidence log

| Task | Commit | Evidence |
| --- | --- | --- |
| — | — | — |
