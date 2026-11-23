---
name: test
description: Write and run targeted deterministic tests for an approved plan or explicitly named files and behavior.
---

Use the plan, files, behavior, and test requirements from the user's current
request. Delegate to the `test-engineer` custom agent with that complete scope.
Instruct it to use the existing framework, write named tests first, avoid live
services and nondeterminism, and run targeted tests only unless broader coverage
is explicitly required. Wait for completion and report every changed test file,
command, failure, unavailable check, and open issue.
