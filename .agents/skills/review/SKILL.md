---
name: review
description: Review the current uncommitted diff for correctness, security, regressions, and missing tests without editing files.
---

Delegate the review focus from the user's current request to the `code-reviewer`
custom agent. Tell it to inspect only the current staged and unstaged diff, skip
generated files, lockfiles, and snapshots, and make no edits. Wait for completion.
Return findings first, ranked blocker, major, then minor, each with file:line and
evidence. Follow with the complete changed-file list, open issues, and known
failing tests. If there are no findings, say so and identify residual test gaps.
