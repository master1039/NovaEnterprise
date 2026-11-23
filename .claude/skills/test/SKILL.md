---
name: test
description: Write and run targeted tests for the requested scope.
argument-hint: "<approved plan path or named files and test requirements>"
context: fork
agent: test-engineer
background: false
---
Your task is $ARGUMENTS. Work from the approved plan in docs/plans/ or the files named in the request. Write the named tests first using existing deterministic fixtures and the existing framework, and run only targeted tests unless the plan says otherwise. Return every changed file, test command, failing test, and open issue.
