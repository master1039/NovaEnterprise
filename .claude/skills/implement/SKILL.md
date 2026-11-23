---
name: implement
description: Implement an approved plan within its file scope.
argument-hint: "<approved plan path or explicitly named files and task>"
context: fork
agent: implementer
background: false
---
Your task is $ARGUMENTS. Read the approved plan in docs/plans/ or work only on files explicitly named in the request. Write named tests first, implement the smallest change, and run targeted tests only unless the plan requires otherwise. Return every changed file, verification result, and open issue.
