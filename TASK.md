# NovaEnterprise — Development task tracker

> Dependency-ordered implementation checklist for GitHub-visible progress.
> Sources: `docs/00-problem.md` · `docs/01-prd.md` · `docs/02-hld.md` · `CLAUDE.md`
>
> The repository is currently an early scaffold. Every item below describes planned work, not existing implementation.

**Branch convention:** `feature/<repo-name>` (one feature branch per sub-task; open each PR against the repository's integration branch)
**Status:** `Pending ❌` · `Completed ✅`

Sub-tasks in the same phase may run in parallel only when the merge-order note permits it. Do not stack one feature branch on another. Merge the listed predecessor before starting work that imports or depends on it.

---

## Phase 1 — Runtime foundation and contracts

> Depends on: nothing. Unblocks: every later phase.
> Merge order: P1-1 first. P1-2, P1-3, and P1-4 may proceed in parallel after it.

| Task | Branch | Status |
|------|--------|--------|
| P1-1 · Python workspace, dependencies, environment template, and Make targets | `feature/runtime-workspace` | Pending ❌ |
| P1-2 · FastAPI app factory, settings, structured logging, and exception handling | `feature/backend-runtime-core` | Pending ❌ |
| P1-3 · Offline pytest harness, fixtures, and deterministic test configuration | `feature/test-harness-offline` | Pending ❌ |
| P1-4 · API contract and frontend-assumption documents | `feature/api-contract-docs` | Pending ❌ |

---

## Phase 2 — Shared schemas and persistence

> Depends on: P1-1 and P1-3. Unblocks: security, retrieval, memory, workflow persistence, and browse APIs.
> Merge order: P2-1 first. P2-2 after P2-1. P2-3 after P2-2. P2-4 after P2-3.

| Task | Branch | Status |
|------|--------|--------|
| P2-1 · Domain enums, API schemas, and normalized `Evidence` contract | `feature/domain-evidence-schemas` | Pending ❌ |
| P2-2 · SQLAlchemy models, database session, migrations, and RLS policies | `feature/database-models-rls` | Pending ❌ |
| P2-3 · Repository layer for records, documents, sessions, events, and audit data | `feature/repository-layer` | Pending ❌ |
| P2-4 · Canonical enterprise sample data and deterministic seed service | `feature/sample-data-seeding` | Pending ❌ |

---

## Phase 3 — Identity, middleware, and safeguards

> Depends on: P1-2 and P2-1. Parallel with: Phases 4 through 9.
> Merge order: P3-1 and P3-3 may run in parallel. P3-2 follows P3-1. P3-4 follows P3-1 and P3-3.

| Task | Branch | Status |
|------|--------|--------|
| P3-1 · JWT validation, role model, and central `require_role` enforcement | `feature/auth-rbac` | Pending ❌ |
| P3-2 · Offline demo login, users, and role-scoped tokens | `feature/auth-demo-tokens` | Pending ❌ |
| P3-3 · Request ID, rate limiting, audit logging, and middleware ordering | `feature/request-guards-middleware` | Pending ❌ |
| P3-4 · Prompt-injection guardrails, secret scrubbing, and approval service | `feature/security-guardrails-approval` | Pending ❌ |

---

## Phase 4 — Provider and storage abstractions

> Depends on: P1-1, P1-2, and P2-1. Unblocks: ingestion, retrieval, graph, memory, and agent development.
> Merge order: P4-1 and P4-2 may run in parallel. P4-3, P4-4, and P4-5 may then run in parallel because they own separate adapters.

| Task | Branch | Status |
|------|--------|--------|
| P4-1 · Provider-agnostic LLM factory and deterministic fake LLM | `feature/llm-provider-factory` | Pending ❌ |
| P4-2 · Embedding factory and deterministic fake embeddings | `feature/embedding-provider-factory` | Pending ❌ |
| P4-3 · Vector-store protocol with memory and Qdrant adapters | `feature/vector-store-adapters` | Pending ❌ |
| P4-4 · Graph-store protocol with memory and Neo4j adapters | `feature/graph-store-adapters` | Pending ❌ |
| P4-5 · Cache and session facade with fake and Redis adapters | `feature/cache-redis-adapters` | Pending ❌ |

---

## Phase 5 — Document ingestion pipeline

> Depends on: P2-3, P2-4, P3-4, P4-2, P4-3, and P4-4.
> Parallel with: Phases 6 through 10 after their own prerequisites merge.
> Merge order: P5-1 first, P5-2 after it, P5-3 after P5-2, and P5-4 last.

| Task | Branch | Status |
|------|--------|--------|
| P5-1 · Markdown, text, and PDF loaders with validated chunking | `feature/ingest-loaders-chunking` | Pending ❌ |
| P5-2 · Entity and relationship extraction with hostile-content flagging | `feature/ingest-entity-extraction` | Pending ❌ |
| P5-3 · Coordinated DB, vector, and graph indexing pipeline | `feature/ingest-indexing-pipeline` | Pending ❌ |
| P5-4 · Ingest command, sample documents, and repeatable bootstrap | `feature/ingest-command-bootstrap` | Pending ❌ |

---

## Phase 6 — Safe SQL retrieval

> Depends on: P2-2, P2-3, and P2-4. Parallel with: Phases 7, 8, 9, and 10.
> Merge order: P6-1 first. P6-2 and P6-3 follow it; keep the validator tests with the validator branch.

| Task | Branch | Status |
|------|--------|--------|
| P6-1 · Read-only SQL parser, allowlist, and injection rejection | `feature/sql-readonly-validator` | Pending ❌ |
| P6-2 · Parameterized SQL templates and evidence-normalizing executor | `feature/sql-retrieval-engine` | Pending ❌ |
| P6-3 · SQL validator, date-range, and canonical incident tests | `feature/sql-retrieval-tests` | Pending ❌ |

---

## Phase 7 — Knowledge graph retrieval

> Depends on: P2-1, P2-4, and P4-4. Parallel with: Phases 6, 8, 9, and 10.
> Merge order: P7-1 first. P7-2 follows P7-1. P7-3 follows P7-2.

| Task | Branch | Status |
|------|--------|--------|
| P7-1 · Typed graph entities, relationships, and seed mapping | `feature/graph-domain-seeding` | Pending ❌ |
| P7-2 · Read-only typed traversals that expose parameterized Cypher | `feature/graph-typed-traversals` | Pending ❌ |
| P7-3 · Customer-impact, ownership, expansion, and degradation tests | `feature/graph-retrieval-tests` | Pending ❌ |

---

## Phase 8 — Hybrid document retrieval

> Depends on: P2-1, P4-2, P4-3, and P5-3. Parallel with: Phases 6, 7, 9, and 10.
> Merge order: P8-1 first, P8-2 after it, and P8-3 last.

| Task | Branch | Status |
|------|--------|--------|
| P8-1 · Semantic and BM25 retrieval with source metadata | `feature/retrieval-vector-bm25` | Pending ❌ |
| P8-2 · Reciprocal-rank fusion, reranking, deduplication, and cutoffs | `feature/retrieval-fusion-rerank` | Pending ❌ |
| P8-3 · Hybrid retrieval relevance and hostile-document tests | `feature/retrieval-hybrid-tests` | Pending ❌ |

---

## Phase 9 — Scoped memory

> Depends on: P2-3 and P4-5. Parallel with: Phases 5 through 8 and 10.
> Merge order: P9-1 first. P9-2 follows it. P9-3 completes the public service and tests.

| Task | Branch | Status |
|------|--------|--------|
| P9-1 · Conversation, user, organizational, and workflow memory schemas | `feature/memory-scope-schemas` | Pending ❌ |
| P9-2 · Short-term and durable memory adapters with tenant/user boundaries | `feature/memory-adapters` | Pending ❌ |
| P9-3 · Recall, record, clear, provenance, and isolation service tests | `feature/memory-service-tests` | Pending ❌ |

---

## Phase 10 — Query analysis and retrieval routing

> Depends on: P2-1, P4-1, and P1-3. Does not wait for retrieval implementations because routing targets shared contracts.
> Merge order: P10-1 first. P10-2 follows it. P10-3 and P10-4 may run in parallel after P10-2.

| Task | Branch | Status |
|------|--------|--------|
| P10-1 · `ResearchState`, graph node contracts, and deterministic routing rules | `feature/workflow-state-rules` | Pending ❌ |
| P10-2 · Intent, entity, time-range, and complexity analysis nodes | `feature/workflow-query-analysis` | Pending ❌ |
| P10-3 · Bounded sub-question decomposition | `feature/workflow-decomposition` | Pending ❌ |
| P10-4 · Vector, SQL, graph, and hybrid routing with shape tests | `feature/workflow-retrieval-routing` | Pending ❌ |

---

## Phase 11 — Evidence, correction, and answer workflow

> Depends on: Phases 6, 7, 8, 9, and 10. Unblocks: the asynchronous research API.
> Merge order: P11-1 first. P11-2 and P11-3 follow it in parallel. P11-4 follows P11-3. P11-5 wires the completed nodes last.

| Task | Branch | Status |
|------|--------|--------|
| P11-1 · Evidence collection, normalization, stable IDs, and deduplication | `feature/workflow-evidence-collection` | Pending ❌ |
| P11-2 · Missing-evidence detection and bounded corrective retrieval | `feature/workflow-corrective-retrieval` | Pending ❌ |
| P11-3 · Claim-to-evidence verification and unsupported-claim handling | `feature/workflow-evidence-verification` | Pending ❌ |
| P11-4 · Answer synthesis and resolvable citation verification | `feature/workflow-answer-citations` | Pending ❌ |
| P11-5 · LangGraph wiring, checkpointing, bounded loops, and workflow tracing | `feature/workflow-graph-wiring` | Pending ❌ |

---

## Phase 12 — Backend APIs and observability

> Depends on: P2-3, Phase 3, P5-3, P7-2, and Phase 11.
> Unblocks: feature-complete frontend screens and the end-to-end evaluation.
> Merge order: P12-1 first. P12-2 and P12-3 follow it. P12-4, P12-5, and P12-6 may proceed in parallel against the written API contract.

| Task | Branch | Status |
|------|--------|--------|
| P12-1 · Research session service, background execution, and resumable persistence | `feature/research-session-service` | Pending ❌ |
| P12-2 · Research create, poll, and session-detail endpoints | `feature/api-research-lifecycle` | Pending ❌ |
| P12-3 · Workflow events, timings, executed-query metadata, and safe observability | `feature/api-workflow-events` | Pending ❌ |
| P12-4 · Validated document upload, browse, delete, and approval endpoints | `feature/api-documents-approval` | Pending ❌ |
| P12-5 · Customer, incident, decision, project, ticket, and graph browse APIs | `feature/api-enterprise-browse` | Pending ❌ |
| P12-6 · Liveness/readiness checks and graceful adapter degradation | `feature/api-health-readiness` | Pending ❌ |

---

## Phase 13 — Frontend shell and browse experience

> Depends on: P1-4 and P3-2. P13-1 and P13-2 may begin before Phase 12 by using the approved contract. Data-backed pages wait for their matching endpoints.
> Merge order: P13-1 and P13-2 in parallel. P13-3 follows both. P13-4 follows P12-5.

| Task | Branch | Status |
|------|--------|--------|
| P13-1 · Next.js application shell, navigation, theme, and error boundaries | `feature/frontend-app-shell` | Pending ❌ |
| P13-2 · Typed API client, request IDs, authentication, and polling utilities | `feature/frontend-api-client` | Pending ❌ |
| P13-3 · Demo login and role-aware navigation/layout | `feature/frontend-auth-layout` | Pending ❌ |
| P13-4 · Read-only enterprise records, documents, and graph explorer pages | `feature/frontend-browse-pages` | Pending ❌ |

---

## Phase 14 — Research and evidence UI

> Depends on: P12-2, P12-3, P13-2, and P13-3.
> Merge order: P14-1 first. P14-2 and P14-3 may run in parallel. P14-4 follows all three.

| Task | Branch | Status |
|------|--------|--------|
| P14-1 · Research question form and session route | `feature/frontend-research-session` | Pending ❌ |
| P14-2 · Two-second polling, workflow progress, queries, timings, and event timeline | `feature/frontend-research-progress` | Pending ❌ |
| P14-3 · Evidence list, citations, missing-evidence warnings, and answer rendering | `feature/frontend-evidence-citations` | Pending ❌ |
| P14-4 · Frontend unit, accessibility, authorization, and degraded-state tests | `feature/frontend-research-tests` | Pending ❌ |

---

## Phase 15 — Evaluation and canonical demo

> Depends on: Phases 11, 12, and 14. P15-1 may begin earlier from the PRD, but scoring waits for the complete workflow.
> Merge order: P15-1 first. P15-2 and P15-3 may run in parallel. P15-4 follows them. P15-5 is the final quality gate.

| Task | Branch | Status |
|------|--------|--------|
| P15-1 · Fixed evaluation dataset for simple, multi-hop, unsafe, and missing-evidence cases | `feature/evaluation-dataset` | Pending ❌ |
| P15-2 · Retrieval, SQL, graph, citation, coverage, and grounding evaluator | `feature/evaluation-metrics` | Pending ❌ |
| P15-3 · API lifecycle, RBAC, upload, injection, and graph-shape integration tests | `feature/integration-acceptance-tests` | Pending ❌ |
| P15-4 · Offline `make demo`, ingest, graph seed, and evaluation commands | `feature/canonical-demo-commands` | Pending ❌ |
| P15-5 · CI thresholds, approximately seven-second latency check, and regression report | `feature/evaluation-quality-gates` | Pending ❌ |

---

## Phase 16 — Integrations and delivery

> Depends on: Phase 12 for deployable services and Phase 15 for release gates.
> Merge order: P16-1 and P16-2 may run in parallel. P16-3 follows P16-2. P16-4 may run with P16-3. P16-5 follows all delivery work.

| Task | Branch | Status |
|------|--------|--------|
| P16-1 · Replaceable document-source protocol, mock integration, and MCP server | `feature/integration-protocols-mcp` | Pending ❌ |
| P16-2 · Backend and frontend container images | `feature/docker-images` | Pending ❌ |
| P16-3 · Compose stack for app, PostgreSQL, Redis, Qdrant, and Neo4j | `feature/docker-compose-stack` | Pending ❌ |
| P16-4 · CI workflow, Terraform scaffold, and secret-safe environment wiring | `feature/delivery-ci-terraform` | Pending ❌ |
| P16-5 · Deployment hygiene, operations runbook, and production-worker guidance | `feature/delivery-operations` | Pending ❌ |

---

## Dependency overview

```text
P1 Runtime and contracts
 ├─► P2 Schemas and persistence
 │    ├─► P3 Identity and safeguards ────────────────────────────────┐
 │    ├─► P4 Providers and stores                                   │
 │    │    ├─► P5 Ingestion ─────────────────────────────────────┐  │
 │    │    ├─► P8 Hybrid retrieval ────────────────┐             │  │
 │    │    └─► P9 Memory ──────────────────────────┤             │  │
 │    ├─► P6 SQL retrieval ────────────────────────┤             │  │
 │    └─► P7 Graph retrieval ──────────────────────┤             │  │
 └─► P10 Analysis and routing ─────────────────────┤             │  │
                                                   ▼             │  │
                                         P11 Evidence workflow   │  │
                                                   └──────┬──────┘  │
                                                          ▼         │
                                                   P12 Backend APIs ◄┘
                                                          │
P1 API contract ─► P13 Frontend shell ────────────────────┤
                                                          ▼
                                                   P14 Research UI
                                                          │
                                                          ▼
                                                   P15 Evaluation
                                                          │
                                                          ▼
                                                   P16 Delivery
```

Phases 3, 4, 6, 7, 9, and most of Phase 10 can proceed in parallel after their shared contracts merge. Phase 5 joins storage adapters with safeguards. Phase 11 is the principal backend join point. The frontend shell begins from the written API contract instead of waiting for the full workflow. Phase 14 joins the frontend shell with the research API.

---

## Progress summary

| Phase | Name | Tasks | Completed |
|-------|------|------:|----------:|
| 1 | Runtime foundation and contracts | 4 | 0 |
| 2 | Shared schemas and persistence | 4 | 0 |
| 3 | Identity, middleware, and safeguards | 4 | 0 |
| 4 | Provider and storage abstractions | 5 | 0 |
| 5 | Document ingestion pipeline | 4 | 0 |
| 6 | Safe SQL retrieval | 3 | 0 |
| 7 | Knowledge graph retrieval | 3 | 0 |
| 8 | Hybrid document retrieval | 3 | 0 |
| 9 | Scoped memory | 3 | 0 |
| 10 | Query analysis and retrieval routing | 4 | 0 |
| 11 | Evidence, correction, and answer workflow | 5 | 0 |
| 12 | Backend APIs and observability | 6 | 0 |
| 13 | Frontend shell and browse experience | 4 | 0 |
| 14 | Research and evidence UI | 4 | 0 |
| 15 | Evaluation and canonical demo | 5 | 0 |
| 16 | Integrations and delivery | 5 | 0 |
| **Total** | | **66** | **0** |

---

## Status rules

- Use `Pending ❌` until the branch is merged and its targeted tests pass.
- Change a row to `Completed ✅` only after merge, not when a branch or PR is opened.
- If a task's scope changes, update its dependency and merge-order notes before implementation.
- A phase is complete only when every row in that phase is `Completed ✅` and its dependent contracts remain green.
