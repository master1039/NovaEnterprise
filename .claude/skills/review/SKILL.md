---
name: review
description: Review the current uncommitted diff for actionable findings.
argument-hint: "<review focus or affected paths>"
context: fork
agent: code-reviewer
background: false
---
Your task is $ARGUMENTS. Review only the current staged and unstaged git diff, skipping generated files, lockfiles and snapshots. Do not edit files. Return findings ranked blocker, major or minor with file:line, followed by all open issues and known failing tests.
