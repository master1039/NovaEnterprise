---
name: plan
description: Create an approval-ready implementation plan for a multi-file, ambiguous, or high-risk repository change; do not implement the change.
---

Treat the user's current request as the complete task input. Delegate it to the
`planner` custom agent with the relevant requirements and paths. Ask the agent to
inspect the repository and write a plan under `docs/plans/` naming every affected
file, tests to write first, verification commands, risks, and approval questions.
Wait for it to finish, then return the plan path, full open-issue list, and a clear
request for approval. Do not implement the plan in this workflow.
