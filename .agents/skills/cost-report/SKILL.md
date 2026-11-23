---
name: cost-report
description: Report observed Codex token usage, cache metrics, and subagent activity without estimating monetary or plan charges.
---

Use only observed data available from the current run, `codex exec --json` output,
or accessible Codex session JSONL. Report the source and, when present,
`input_tokens`, `cached_input_tokens`, output tokens, reasoning tokens, and cache
hit ratio (`cached_input_tokens / input_tokens`). For subagents, list observed
spawn counts by agent role and any explicitly requested model overrides. State
"unavailable" for metrics not present; do not infer missing values. Never convert
tokens into currency, estimate subscription or plan charges, or claim cache
savings that the observed fields do not establish. Do not expose prompt text,
credentials, or unrelated session content.
