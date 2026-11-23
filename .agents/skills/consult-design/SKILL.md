---
name: consult-design
description: Obtain a concise read-only answer to one narrow architecture or design question; never use it for implementation.
---

Extract the single design question and relevant paths from the user's current
request. Delegate only that question to the `design-consultant` custom agent.
Require a read-only response of 300 words or fewer containing the recommendation,
key trade-offs, and any one-sentence blocker. Wait for completion and return the
answer without expanding its scope. Do not edit files in this workflow.
