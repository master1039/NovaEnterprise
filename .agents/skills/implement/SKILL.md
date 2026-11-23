---
name: implement
description: Implement an approved repository plan or an explicitly file-scoped change, with tests and targeted verification.
---

Use the approved plan path or explicit file scope in the user's current request.
Delegate the implementation to the `implementer` custom agent, passing the full
approved scope and acceptance criteria. Instruct it to write named tests first,
make only the approved changes, and run targeted checks. Wait for it to finish,
inspect its result and diff, then report every changed file, command result,
failing test, and open issue. Stop if no approved plan or explicit file scope exists.
