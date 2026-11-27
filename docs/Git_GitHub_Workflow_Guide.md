# Git and GitHub Workflow Guide

NovaEnterprise — Enterprise Knowledge and Decision Intelligence Platform

*Version 1.0 | Last updated: November 27, 2026*

| | |
|---|---|
| Audience | Backend, frontend, retrieval, agents, infrastructure, and QA contributors |
| Repository | https://github.com/master1039/NovaEnterprise.git |
| GitHub account | `master1039` |
| Default integration branch | `development` |
| Long-lived branches | `development`, `testing`, `master` |
| Task tracker | `TASK.md` — one `feature/<name>` branch per sub-task |
| Current state | Phases 1–9 merged; Phase 10 query analysis implemented on its feature branch |

This guide defines how code moves through NovaEnterprise. Feature work branches
from `development` and returns through a pull request. `testing` and `master` are
promotion branches for staging validation and production candidates. A merge is
not the same as a deployment.

## Contents

1. Branch model
2. Before starting
3. First-time setup
4. Daily feature workflow
5. Pull requests
6. Promotions and hotfixes
7. Branch and commit naming
8. Project checks
9. Quick reference
10. Help and ownership

## 1. Branch model

| Branch | Purpose | Who merges here | Represents |
|---|---|---|---|
| `development` | Integration branch for active work | Contributors through reviewed PRs | Development/integration |
| `testing` | Phase validation and staging candidate | Release owner | QA/staging candidate |
| `master` | Code approved to ship | Release owner | Production candidate |

### Rules

- Create feature branches from an up-to-date `development` branch.
- Open feature and ordinary bug-fix pull requests into `development`.
- Do not push directly to `development`, `testing`, or `master`.
- Do not stack one feature branch on another. Merge the predecessor named in
  `TASK.md` before starting dependent work.
- One `TASK.md` sub-task maps to one feature branch and one pull request.
- Mark a task `Completed ✅` only after its PR is merged and targeted checks pass.
- Promote with PRs in this order: `development` → `testing` → `master`.
- Treat directories named in task or agent instructions as scope guidance, not
  proof of enforced filesystem permissions.
- Never claim that a merge deployed an environment. Record deployment separately.

## 2. Before starting

### Access and security

- Use a GitHub account with write access to `master1039/NovaEnterprise`.
- Enable two-factor authentication.
- Prefer GitHub CLI over HTTPS or use an existing SSH key.
- Never store GitHub tokens, API keys, service credentials, or private keys in
  the repository.

### Recommended tools

| Tool | Version | Notes |
|---|---|---|
| Git | 2.40+ | PowerShell commands are used in this guide. |
| GitHub CLI (`gh`) | Current | Recommended for creating and reviewing PRs. |
| Python | 3.12 | Required by `pyproject.toml`. |
| Node.js | 22 | Planned Next.js frontend runtime. |
| Docker | Current | Planned local multi-service stack. |

Verify installed tools:

```powershell
git --version
gh --version
python --version
node --version
docker --version
```

`gh` is optional; create PRs in the GitHub web interface when it is unavailable.

### Read first

| Document | Purpose |
|---|---|
| `AGENTS.md` | Current repository layout, commands, conventions, and Codex routing |
| `CLAUDE.md` | Target architecture, safety rules, and implementation constraints |
| `TASK.md` | Dependency order, sub-task ID, branch name, and status |
| `docs/00-problem.md` | Business problem and canonical multi-store question |
| `docs/01-prd.md` | Functional and non-functional requirements |
| `docs/02-hld.md` | Target layers, adapters, workflow, and dependency direction |
| `docs/API_CONTRACT.md` | API contract after task P1-4 creates it |
| `docs/FRONTEND_ASSUMPTIONS.md` | Frontend assumptions after task P1-4 creates it |

The design documents describe target behavior. Inspect the repository before
assuming a file, command, service, or test already exists.

## 3. First-time setup

The remote is populated and already contains `master`, `development`, and
`testing`. Clone it; do not reseed it as an empty repository.

### Clone a new working copy

```powershell
git clone https://github.com/master1039/NovaEnterprise.git
Set-Location NovaEnterprise
git fetch origin --prune
git checkout development
git pull --ff-only origin development
```

SSH alternative:

```powershell
git clone git@github.com:master1039/NovaEnterprise.git
```

### Connect an existing working copy

Only add the remote when `git remote -v` shows that `origin` is missing.

```powershell
git remote add origin https://github.com/master1039/NovaEnterprise.git
git fetch origin --prune
git checkout development
git branch --set-upstream-to=origin/development development
```

Set tracking for an existing local promotion branch when needed:

```powershell
git branch --set-upstream-to=origin/testing testing
git branch --set-upstream-to=origin/master master
```

### Configure Git identity

```powershell
git config --global user.name "Your Full Name"
git config --global user.email "you@example.com"
```

Use the email attached to the GitHub account. Do not put credentials in Git
configuration committed to this repository.

### Authenticate GitHub CLI (optional)

```powershell
gh auth login
```

Choose HTTPS or SSH and complete authentication outside the repository.

### Current local runtime

Phases 1 through 9 provide the Python workspace, FastAPI shell, relational
persistence, deterministic sample data, local authentication and request
safeguards, offline provider/store adapters, safe document ingestion, tests,
quality commands, AST-validated tenant-scoped SQL retrieval, and typed graph
retrieval, semantic and BM25 document search, rank fusion, reranking,
source-aware Evidence, explicit degradation, and isolated memory scopes with
provenance. The Phase 10 feature branch adds typed, bounded query analysis,
decomposition, and retrieval routing:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m backend.app.services.seed
.\.venv\Scripts\python.exe -m backend.app.ingestion.command --dry-run
```

With GNU Make installed, use `make setup`, `make run`, `make check`,
`make db-upgrade`, `make seed`, `make ingest-dry-run`, and `make ingest`. The
frontend and multi-service stack remain later-phase work.

## 4. Daily feature workflow

Follow this cycle for every row in `TASK.md`.

### Step 1 — Confirm the task and predecessor

Read the phase's `Depends on` and `Merge order` notes. Confirm every required
predecessor is already merged into `development`.

Example Phase 10 task implemented on its independent feature branch:

```text
P10-2 · Intent, entity, time-range, and complexity analysis nodes
Branch: feature/workflow-query-analysis
```

### Step 2 — Sync `development`

```powershell
git checkout development
git pull --ff-only origin development
git status
```

Start only when the working tree is clean or when all existing changes are
understood and intentionally preserved.

### Step 3 — Create the feature branch

Copy the exact branch name from `TASK.md`.

```powershell
git checkout -b feature/domain-evidence-schemas
```

Examples from the tracker:

- `feature/domain-evidence-schemas` — P2-1 shared domain contracts
- `feature/sql-readonly-validator` — P6-1 safe SQL validation
- `feature/graph-domain-seeding` — P7-1 typed graph seeding
- `feature/workflow-graph-wiring` — P11-5 LangGraph wiring
- `feature/frontend-research-progress` — P14-2 research progress UI

### Step 4 — Implement and verify

- Work only within the task's approved scope.
- Write named tests first when the test harness exists.
- Keep offline behavior deterministic.
- Run targeted checks before broader suites.
- Update API contracts with backend schemas and frontend types in the same PR.
- Treat retrieved documents and tool results as untrusted data.
- Do not expose hidden reasoning; expose decisions, queries, evidence, and timing.

Stage explicit paths rather than `git add .`:

```powershell
git add <task-files-and-tests>
git status
git commit -m "feat(schemas): add domain and evidence contracts"
```

### Step 5 — Push and open a PR

```powershell
git push -u origin feature/domain-evidence-schemas
```

With GitHub CLI:

```powershell
gh pr create `
  --base development `
  --head feature/domain-evidence-schemas `
  --title "feat(schemas): add domain and evidence contracts" `
  --body "## Summary`n- Add shared domain and evidence schemas.`n`n## Related task`n- TASK.md: P2-1`n`n## Test plan`n- [ ] Run targeted schema tests`n- [ ] make check"
```

In PowerShell, the backtick continues a command onto the next line.

### Step 6 — Address review

Add focused follow-up commits to the same branch and push again:

```powershell
git add <reviewed-paths>
git commit -m "fix(runtime): address workspace review"
git push
```

Do not open a second PR for the same sub-task.

### Step 7 — After merge

```powershell
git checkout development
git pull --ff-only origin development
git branch -d feature/domain-evidence-schemas
git fetch origin --prune
```

Delete the remote branch after merge. Change the task to `Completed ✅` in the
same PR when practical; otherwise update it in the next appropriate docs PR.

## 5. Pull requests

### Target branches

| Source | PR base |
|---|---|
| `feature/*` | `development` |
| `bugfix/*` | `development` |
| `hotfix/*` | `master`, then backport to `testing` and `development` |
| `development` promotion | `testing` |
| `testing` promotion | `master` |

### Title examples

- `feat(api): add asynchronous research lifecycle`
- `feat(rag): add typed graph traversals`
- `fix(security): reject unsafe SQL comments`
- `test(workflow): cover bounded corrective retrieval`
- `docs: document API and frontend contracts`

### PR description template

```markdown
## Summary
- What changed and why.

## Related task
- TASK.md: P6-1 · Read-only SQL parser, allowlist, and injection rejection
- Requirements: F7, N1

## Test plan
- [ ] Targeted tests pass offline
- [ ] Broader checks required by the phase pass
- [ ] No secret, database, checkpoint, or generated runtime data is in the diff

## Evidence / notes
- Commands run and their results
- Screenshots for UI changes
- Checks that could not run and why
```

### Before requesting review

- Re-read the `TASK.md` dependency and scope.
- Merge or rebase the latest `origin/development` when the base moved.
- Run every check that currently exists for the affected layer.
- Report every failing test and unavailable check.
- Confirm no `.env`, credential, database, checkpoint, plan file, or private key
  is present in the diff.
- For route or payload changes, update the API contract, backend schema, tests,
  and frontend types together.
- For migrations, add a new migration; do not rewrite a migration already applied.
- Keep generated files, lockfile changes, and dependency additions intentional.
- Do not present target architecture as already implemented.

## 6. Promotions and hotfixes

Promotion uses pull requests between long-lived branches. Feature authors do not
merge feature branches directly into `testing` or `master`.

### `development` → `testing`

Promote when the phase exit criteria are met and `development` is ready for QA.

Checklist:

- CI is green, or the PR explicitly says CI has not run.
- Targeted and phase-level offline checks pass.
- `make demo` passes once P15-4 introduces it.
- Migrations are additive and backward compatible.
- No secrets or local runtime data are tracked.
- The release notes identify incomplete or degraded adapters.

### `testing` → `master`

Promote only after QA accepts the staging candidate.

Checklist:

- QA results and known limitations are documented.
- Security checks are acceptable, or clearly identified as not yet available.
- Evaluation thresholds pass once P15-5 introduces them.
- The rollback target is identified.
- Deployment remains a separate reviewed operation.

### Hotfixes

Create an urgent production fix from `master`:

```powershell
git checkout master
git pull --ff-only origin master
git checkout -b hotfix/<fault-name>
```

Open the first PR into `master`. After it merges, backport the same fix to
`testing` and `development` so the branches do not diverge.

## 7. Branch and commit naming

### Branches

| Pattern | Use | Create from | Merge into |
|---|---|---|---|
| `feature/<name>` | One `TASK.md` sub-task | `development` | `development` |
| `bugfix/<name>` | Ordinary defect outside a tracker row | `development` | `development` |
| `hotfix/<name>` | Urgent production fix | `master` | `master`, then backport |

Rules:

- Use the exact branch in `TASK.md` when a row already defines one.
- Use lowercase hyphen-separated names.
- Describe the capability or fault, not a person or ticket like `wip-2`.
- Do not reuse a branch for a second sub-task.

### Commits

Use small, present-tense commits with an optional scope:

```text
feat(core): add provider-agnostic LLM factory
feat(graph): add customer impact traversal
fix(sql): reject multi-statement queries
test(api): cover research session polling
docs: record frontend API assumptions
chore: update development dependencies
infra(compose): add local graph service
```

Preferred prefixes: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `perf`,
and `infra`.

## 8. Project checks

Run checks only after the corresponding task creates them. Never report a
planned command as passing before it exists.

| Check | Command | Available after |
|---|---|---|
| Current Python smoke | `python main.py` | Now |
| Current syntax check | `python -m compileall main.py src` | Now |
| Offline test suite | `make test` | Now |
| Lint and format checks | `make lint` and `make format-check` | Now |
| Canonical demo | `make demo` | P15-4 |
| Ingestion | `make ingest` | P5-4/P15-4 |
| Graph seeding | `make seed-graph` | P7-1/P15-4 |
| Evaluation | `.venv\Scripts\python.exe -m tests.evaluation.evaluate` | P15-2 |
| Frontend checks | `npm run lint` and `npm run test -- --run` | Frontend phases |
| Compose validation | `docker compose config -q` | P16-3 |

### Required behavior once implemented

- `POST /api/v1/research` returns `202` immediately with a running session.
- The canonical question uses SQL, graph, and hybrid retrieval with citations.
- A simple document question uses one vector sub-question.
- SQL and graph access remain parameterized, allowlisted, and read-only.
- The hostile vendor document is indexed as data and never obeyed as an
  instruction.
- Every substantive answer claim resolves to evidence.
- Viewer, analyst, and admin permissions follow the PRD.
- Destructive document operations require approval.
- The offline fake-provider path requires no API key or external service.
- Graph-store failure degrades affected work without crashing the entire flow.
- Hidden chain-of-thought is never exposed.

## 9. Quick reference

```powershell
git checkout development
git pull --ff-only origin development
git checkout -b feature/<task-branch>

# Work, run targeted checks, stage explicit paths, and commit.
git push -u origin feature/<task-branch>
gh pr create --base development --head feature/<task-branch>

# After merge:
git checkout development
git pull --ff-only origin development
git branch -d feature/<task-branch>
git fetch origin --prune
```

Promotion flow:

```text
development  --PR-->  testing  --PR-->  master  --reviewed deploy--> environment
```

## 10. Help and ownership

- Task choice, dependencies, and branch name: `TASK.md`.
- Repository conventions and current commands: `AGENTS.md`.
- Product requirements: `docs/01-prd.md`.
- Architecture and layer boundaries: `docs/02-hld.md` and `CLAUDE.md`.
- Branch protection, releases, and deployment approval: repository/release owner.

When the shape of a change is unclear, open a draft PR into `development` early
and state the unresolved design question rather than guessing.
