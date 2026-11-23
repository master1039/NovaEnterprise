---
name: plan
description: Write an implementation plan for approval.
argument-hint: "<task and relevant paths>"
context: fork
agent: planner
background: false
---
Your task is $ARGUMENTS. Inspect relevant project requirements and code, then write a plan under docs/plans/ listing every affected file, named tests to write first, and targeted verification commands. Return the plan path, approval questions, and open issues; do not implement it.
