# Security checklist before real-money launch

- Replace all sample secrets; never commit `.env`.
- Use HTTPS and set the Mini App URL to the exact production origin.
- Keep `BOT_TOKEN`, database credentials, and provider secrets server-side only.
- Validate Telegram `initData` server-side and reject stale data.
- Add rate limits to task completion, withdrawal, and referral endpoints.
- Task completion must be backed by trusted provider callbacks or manual admin verification. The included demo completion route is intentionally not an automatic payout mechanism.
- Use an append-only ledger and database transactions for balance changes.
- Require two-person review or extra confirmation for large manual balance adjustments.
- Add audit logs, backups, alerts, fraud detection, and dispute procedures.
- Do not advertise guaranteed earnings. Clearly publish task eligibility, payout limits, processing time, and terms.
