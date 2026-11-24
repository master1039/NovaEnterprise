# Phase 5 Explained — Turning Files into Safe, Searchable Knowledge

## The simple idea

Before Phase 5, NovaEnterprise had a database and empty connections to search
and graph tools. Phase 5 builds the loading dock between ordinary files and
those systems. It accepts a document, checks it, divides it into manageable
pieces, identifies useful business names, and files each result in the right
place.

Think of an office librarian receiving a report. The librarian does not blindly
follow sentences inside the report. They label the report as outside material,
copy only safe information, create index cards, and link mentioned people or
services in a catalogue.

## What happens to one document

1. **Validate the package.** Only Markdown, plain text, and PDF files are
   accepted. Empty, oversized, unsupported, invalid, or unreadable files stop
   immediately.
2. **Give it a safe label.** The system keeps only the filename for source
   metadata. It never publishes the operator's private folder path.
3. **Split it predictably.** Long text becomes overlapping chunks. The overlap
   prevents a sentence near a boundary from losing its context. The same input
   always produces the same document and chunk identifiers.
4. **Treat every word as untrusted.** Phase 3 guardrails inspect every chunk.
   A sentence such as “ignore previous instructions” is recorded as hostile
   data, never executed. Recognizable secrets are redacted.
5. **Recognize business references.** A deterministic extractor identifies
   canonical items such as `INC-2031`, Payments API, and Acme Bank, then creates
   “document mentions entity” relationships.
6. **Write three useful views.** SQLite stores the document and chunks, the
   vector store keeps meaning-based search entries, and the graph store keeps
   named entities and relationships.
7. **Report honestly.** If SQLite succeeds but a search or graph adapter fails,
   the result is `partial`, not `completed`.

## Why repeating the command is safe

Identifiers come from the tenant, source, content, and chunk position. Storage
uses upsert behavior, so running ingestion twice updates the same records rather
than creating duplicates. When Phase 2 already seeded the same tenant and
source file, Phase 5 reuses that document record instead of creating a second
copy. Tenant A and Tenant B still receive different internal identities when
they ingest the same new filename.

## How to demonstrate it

This command validates every sample document and prints counts without writing:

```powershell
.\.venv\Scripts\python.exe -m backend.app.ingestion.command --dry-run
```

This command performs the repeatable local ingestion:

```powershell
.\.venv\Scripts\python.exe -m backend.app.ingestion.command
```

The default demonstration is completely local: SQLite is a file, and vector
and graph stores live in the Python process. No cloud account, API key, Docker
container, Qdrant server, or Neo4j server is required.

## Recruiter-ready summary

“Phase 5 converts company documents into safe, searchable, connected knowledge.
It validates files, preserves context, blocks instruction-like text from taking
control, removes secrets, and indexes the same trusted result across a database,
semantic search, and a knowledge graph. It is repeatable, tenant-isolated, and
honest about partial failures.”
