# Phase 7 Explained — Following the Connections Between Business Records

## The simple idea

Phase 7 helps NovaEnterprise answer questions whose answer lives in connections,
not in one document or database row. For example, a customer is connected to an
incident, the incident is connected to a service, and the service is connected
to its owning team.

Think of a wall map with labelled cards and strings. The cards are customers,
services, incidents, decisions, and teams. The strings explain relationships
such as “incident impacted customer” and “service owned by team.” Phase 7 builds
that map from trusted database records and follows only approved kinds of string.

## What the system does

1. It reads one tenant's relational records.
2. It creates typed graph nodes for teams, services, customers, incidents, and
   decisions.
3. It creates typed relationships such as `OWNED_BY`, `AFFECTED`, `IMPACTED`,
   and `ADDRESSES`.
4. It checks that every relationship points to records that actually exist.
5. It provides fixed, read-only traversals for customer impact, service
   ownership, and bounded node expansion.
6. Values such as service IDs and dates remain parameters; they never become
   executable Cypher text.
7. Results become citation-ready `Evidence`, just like SQL retrieval results.
8. If the graph adapter is unavailable, the result says `degraded` instead of
   inventing an answer or crashing the wider workflow.

## Easy example

For “Which customers were impacted by the Payments API last quarter?”, the
system starts at the Payments API node, follows incoming `AFFECTED` links to
incidents in the requested time window, then follows `IMPACTED` links to
customers. Duplicate customers are removed and the answer remains ordered and
bounded.

## Recruiter-ready summary

“Phase 7 turns separate enterprise records into a safe relationship map. It can
trace a service to incidents, affected customers, and the owning team using
fixed tenant-scoped traversals. Every result is evidence-backed, parameterized,
bounded, and able to degrade safely when a graph service is unavailable.”
