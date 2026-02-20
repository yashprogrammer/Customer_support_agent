# API Troubleshooting

## High latency
- Check request volume spikes in your metrics dashboard.
- Retry with exponential backoff for transient 5xx errors.
- Contact support with request IDs and timestamps.

## 401 Unauthorized
- Verify your API key has not expired.
- Confirm the `Authorization` header uses the correct bearer token format.

## 429 Rate Limited
- Respect `Retry-After` header.
- Reduce concurrency or upgrade to a higher plan for better limits.
