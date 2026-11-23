# Payments API Outage Postmortem

On 2026-07-14 a processor retry storm exhausted the Payments API connection pool, impacting Acme Bank, Globex Retail, and Initech. We adopted retry budgets, exponential backoff, circuit breakers, and pool saturation alerts.
