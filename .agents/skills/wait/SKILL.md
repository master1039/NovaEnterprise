---
name: wait
description: Wait for a named background agent task to finish, then summarize its result in three lines or fewer.
---

Identify the background task named in the user's current request. Do no new work
while it is still running. Wait using the available subagent coordination tools;
do not busy-poll. When it completes, summarize its result in three lines or fewer,
including any failure or unfinished work. If no such task exists, report that
fact instead of starting one.
