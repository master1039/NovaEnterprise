---
name: cost-report
description: Summarise session usage and agent spawn costs.
argument-hint: "<session identifier or reporting scope>"
context: fork
agent: general-purpose
model: haiku
background: false
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---
Your task is $ARGUMENTS. If scripts/claude_usage/report.py exists, run it with the working Python command and summarise its output. Otherwise, read the relevant session transcript and its subagents/ folder under ~/.claude/projects/<project>/. Read only usage metadata needed for the report; do not expose credentials or unrelated session content. In both cases, then read .claude/agent-calls.jsonl and list, per agent type: spawn count, models requested, blocked calls, and the description of every general-purpose spawn. Report missing files or unavailable usage data explicitly. Mention that /usage shows the main session's totals for free.
