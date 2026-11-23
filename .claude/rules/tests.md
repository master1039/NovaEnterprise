---
paths:
  - "tests/**"
---
# Test conventions

- Use the project's existing test framework; do not add a new framework without approval.
- Write the tests named in the approved plan or request before changing the corresponding behavior.
- Every bug fix needs a regression test that fails without the fix.
- Keep tests deterministic: no network calls, real external services, or sleeps; use fixtures and mocks.
- Cover empty inputs, boundaries, authorization failures, missing dependencies, and invalid evidence when relevant.
- Assert evidence, routing, citations, and safety rather than exact nondeterministic prose.
- Run targeted tests unless the approved plan explicitly calls for a broader suite.
- Report every failing test and any verification that could not run.
