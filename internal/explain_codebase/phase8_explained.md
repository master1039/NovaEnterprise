# Phase 8 Explained — Finding the Best Passage in Company Documents

## The simple idea

Phase 8 gives NovaEnterprise two ways to search the same company documents and
then combines their strengths.

Imagine asking a librarian for information about “payment delays affecting
Acme Bank.” One librarian looks for the exact words *payment*, *delay*, and
*Acme*. Another understands that *slow checkout* and *payment latency* describe
similar ideas. Phase 8 asks both librarians, compares their ranked lists, and
returns the strongest passages only once.

## What the system does

1. It accepts a question for one company tenant.
2. Semantic search converts the question into numbers and compares them with
   the stored document vectors. This finds passages with similar meaning.
3. BM25 search looks through that tenant's stored chunks for important matching
   words. Rare, useful words count more than common words.
4. Reciprocal-rank fusion combines both result lists. A passage recommended by
   both methods receives more confidence.
5. A small deterministic reranker considers term overlap, removes duplicate
   chunks, applies the requested score cutoff, and enforces a hard result limit.
6. Every result becomes shared `Evidence` with a stable ID, document title,
   source filename, page, chunk, score, and resolvable locator.
7. Document text is treated only as untrusted data. Flagged prompt-injection
   text is placed inside a visible safety boundary, and secrets are redacted.
8. If vector search is unavailable, BM25 can still return an explicitly
   `partial` result. The system reports the redacted failure rather than
   pretending that both search methods succeeded.

## Easy example

For “Why was Acme Bank checkout slow?”, BM25 may find a passage containing
“Acme Bank,” while semantic search finds another passage saying “Payments API
latency.” Fusion rewards a passage found by both methods and returns the best
evidence with its original document and page information.

## What Phase 8 does not do

It does not write an answer, follow instructions found inside documents, call a
live AI service during tests, or expose another tenant's documents. A later
workflow will use this evidence to compose and verify answers.

## Recruiter-ready summary

“Phase 8 builds a safe hybrid document search. It combines meaning-based vector
search with precise keyword search, fuses and reranks the results, removes
duplicates, preserves citations, and continues transparently in a partial mode
when one search adapter is unavailable.”
