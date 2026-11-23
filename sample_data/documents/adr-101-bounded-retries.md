# ADR 101: Bounded Processor Retries

The Payments API uses exponential backoff, retry budgets, and circuit breakers so a failing processor cannot consume every connection.
