# Phase 9 Explained — Giving the System Safe, Separate Memory

## The simple idea

Phase 9 lets NovaEnterprise remember useful information without mixing together
different companies, people, conversations, or automated workflows.

Think of four clearly labelled notebooks:

1. **Conversation memory** holds details needed only in the current discussion.
2. **User memory** holds a person's durable preferences, such as preferring a
   concise answer.
3. **Organizational memory** holds shared company facts, such as the fiscal
   calendar or citation policy.
4. **Workflow memory** holds temporary progress for one research run.

The notebooks may look similar, but the system never treats them as one pile.

## How it works

When a fact is recorded, the memory service first identifies the company,
person, session, and requested notebook. Conversation and workflow facts go to
an expiring cache because they are temporary. User and organizational facts go
to the database because they must survive a cache restart. Existing company
facts seeded in Phase 2 remain visible through the organizational scope.

Every memory includes its source and optional supporting details. This answers
the important question, “Where did the system learn this?” Secrets such as API
keys and passwords are removed before anything is stored.

When memory is recalled, the same ownership labels are applied again. A user
cannot read another user's preferences, one conversation cannot see another
conversation's notes, and one company cannot see another company's facts.
Results are consistently ordered and limited so a request cannot return an
unbounded amount of data.

Clearing memory is equally precise. Clearing one user's preferences does not
remove organizational policy, another user's preferences, or conversation
history.

## What happens if storage is unavailable?

The service reports a `degraded` result with a secret-redacted error. It does
not invent remembered information or claim that the operation succeeded.

## What Phase 9 does not do

Memory is context, not proof. It does not replace the cited SQL, graph, and
document evidence created by earlier phases. Phase 9 also adds no public HTTP
endpoint; later workflow and API phases will expose these capabilities safely.

## Recruiter-ready summary

“Phase 9 gives the platform four isolated memory scopes. Temporary conversation
and workflow state uses an expiring cache, durable user and company knowledge
uses tenant-scoped persistence, every item keeps provenance, secrets are
redacted, and failures are reported honestly rather than fabricating memory.”

