# Phase 11 Explained — Turning Research Results into a Trustworthy Answer

## The simple idea

Phase 10 created a research plan. Phase 11 runs that plan and acts like a careful
editor: it gathers findings from different specialists, checks whether every
part of the question has evidence, retries missing parts once, rejects claims
that the evidence does not support, and attaches citations to the final answer.

## What happens step by step

1. Each planned sub-question is sent to its selected retrieval specialist.
2. SQL, graph, and document results arrive in the same `Evidence` format.
3. Duplicate findings are stored once, while the system remembers every
   sub-question that found them.
4. Missing sub-questions are detected. The workflow may perform a configured
   corrective round—one by default—and can never retry forever.
5. Candidate claims must name their supporting evidence. A conservative check
   rejects unresolved sources, extra unsupported facts, and hostile document
   instructions.
6. Only supported claims enter the answer. Stable markers such as `[1]` point
   to a real Evidence locator.
7. A final citation check reports missing, unused, or ambiguous references.

## What checkpointing means

LangGraph saves the workflow state under a thread identifier after each step.
That gives the later API layer a resumable and inspectable process rather than
one large invisible function. The trace records node names, counts, status, and
safe errors—not private chain-of-thought.

## Failure behavior

One failed retrieval does not erase successful findings from other paths.
Failures are secret-redacted, missing coverage remains visible, and the answer
says that evidence is insufficient instead of inventing a result.

## What Phase 11 does not do

It does not expose an HTTP research endpoint or launch background workers yet;
those belong to Phase 12. Retrieval implementations remain separate and are
injected into the workflow, keeping orchestration testable offline.

## Recruiter-ready summary

“Phase 11 is the trust layer of the research system. It coordinates multiple
search paths, retries missing evidence within a strict limit, verifies every
claim, produces resolvable citations, and checkpoints each visible workflow
step so failures never turn into fabricated answers.”
