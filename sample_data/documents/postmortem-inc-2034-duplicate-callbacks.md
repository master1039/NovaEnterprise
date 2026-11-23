# Duplicate Payment Callback Postmortem

Missing idempotency keys allowed retry callbacks to be delivered twice to Globex Retail and Umbrella Health. Every callback is now assigned a persisted idempotency key.
