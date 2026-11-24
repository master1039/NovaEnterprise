# Phase 6 Explained — Asking the Database Without Risking the Database

## The simple idea

Phase 6 lets NovaEnterprise answer exact business questions from structured
records. Documents are useful for explanations, but questions such as “Which
Payments API incidents happened last quarter?” need exact dates and rows from a
database.

Think of the database as a secure records room. The system may look through an
approved window, but it cannot enter the room, move a folder, or destroy a
record. Every request is checked before the database sees it.

## What happens to one question

1. **Choose an approved question shape.** The application uses a typed template
   for incidents belonging to a service during a date range.
2. **Keep values separate from instructions.** A service name and dates are
   sent as bound parameters. Even text that looks like SQL remains an ordinary
   value and cannot become a second command.
3. **Inspect the SQL structure.** SQLGlot converts the query into a syntax tree.
   NovaEnterprise permits one bounded `SELECT` and rejects writes, comments,
   multiple statements, hidden subqueries, unknown tables or columns, unsafe
   functions, and wildcard access.
4. **Require tenant isolation.** Every table must contain an explicit
   `tenant_id = :tenant_id` condition. A caller cannot remove this parameter or
   substitute another tenant through the query template.
5. **Limit the result.** Every approved query has a small deterministic limit
   and ordering, preventing accidental bulk reads and inconsistent results.
6. **Convert rows into evidence.** Each incident becomes the same shared
   `Evidence` shape used by future document and graph retrieval. It carries a
   stable ID, source record, locator, safe content, executed query shape, and
   useful metadata.
7. **Fail safely.** Database errors are secret-redacted and do not turn a failed
   lookup into a fabricated answer.

## Easy example

The question asks for Payments API incidents from July through September. The
template binds `Payments API`, the start time, the exclusive end time, and the
current tenant. The database returns matching incidents in date order. Phase 6
then produces evidence such as `inc-2031` and `inc-2034`, with locators that a
later answer can cite.

If somebody supplies a service name like:

```text
Payments API' OR 1=1; DROP TABLE incidents; --
```

it is treated only as a service name. It matches no service and returns an
empty list; it never becomes executable SQL.

## What Phase 6 does not do

Phase 6 does not let an AI model freely write and execute database commands. It
does not modify records, expose every table, or bypass application roles. Later
workflow phases decide when SQL retrieval is appropriate; this phase supplies
the narrow, safe retrieval boundary.

## Recruiter-ready summary

“Phase 6 gives the platform exact answers from business records without giving
an AI unrestricted database access. It uses approved parameterized templates,
parses and allowlists every query, forces tenant isolation and result limits,
and converts database rows into traceable evidence for cited answers.”
