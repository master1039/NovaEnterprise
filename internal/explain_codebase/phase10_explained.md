# Phase 10 Explained — Turning One Big Question into a Safe Research Plan

## The simple idea

Phase 10 is the planner between a person's question and the search systems built
in earlier phases. It does not search or write an answer yet. It decides what
the question means, whether it contains several jobs, and which specialist
should handle each job.

Imagine a research coordinator receiving this question:

> Which customers were impacted by the Payments API last quarter, what
> incidents occurred, which teams own those services, and what decisions were
> taken to prevent recurrence?

The coordinator recognizes the service name, the relative time phrase, and four
different information needs. It creates four smaller questions and sends them
to the right future search paths: relationships to the graph, exact incident
records to SQL, and decision explanations to hybrid document search.

## What happens step by step

1. `ResearchState` provides one validated envelope for the original question,
   analysis, sub-questions, routing plan, decisions, and safe errors.
2. Query analysis identifies intent, named business entities, and time wording.
   Relative phrases such as “last quarter” remain relative; the system does not
   invent dates without an agreed reference date.
3. Complexity assessment labels the request `simple`, `moderate`, or `complex`
   using visible deterministic rules.
4. Decomposition creates at most `NOVA_MAX_SUBQUESTIONS` items, four by default.
   Stable IDs such as `sq1` make later progress easy to follow.
5. Routing assigns each sub-question to vector, SQL, graph, or hybrid retrieval
   and records a short reason code.

## Safety and reliability

An optional AI provider may suggest entities or time wording only when those
exact words appear in the question. Invalid JSON, a provider failure, or a
hallucinated value is rejected and deterministic rules continue the plan.
Errors are secret-redacted.
Prompt-injection wording in a question is flagged and treated as data; it cannot
replace the routing rules. Decomposition is bounded, so this phase cannot create
an endless agent loop.

## What Phase 10 does not do

It does not execute SQL, traverse the graph, search documents, or generate an
answer. Those actions belong to retrieval and later workflow phases. Phase 10
produces a typed, inspectable plan that those phases can safely consume.

## Recruiter-ready summary

“Phase 10 turns a natural-language business question into a controlled research
plan. It identifies intent, entities, and time scope, breaks complex requests
into a bounded set of smaller questions, and routes each one to the appropriate
enterprise search system with deterministic fallbacks and visible decisions.”
