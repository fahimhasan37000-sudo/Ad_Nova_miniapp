# Telegram Earning Mini App — Starter

A starter project for a Telegram Mini App with a FastAPI backend, PostgreSQL, aiogram bot, and a separate admin panel.

## Included
- Telegram Mini App authentication via Telegram `initData` validation on the server
- User profile and balance summary
- Task listing and task completion endpoint with server-side idempotency
- Referral link generation and referral bonus ledger entry (bonus activates only after referred user completes a qualifying task)
- Withdrawal requests with minimum balance check and admin review endpoints
- Admin API protected by an explicit `ADMIN_TELEGRAM_IDS` allowlist
- Simple mobile-first Mini App and admin interface
- PostgreSQL schema and Docker Compose

## Important
This is a starter, not a production-ready money platform. Before real payouts:
- Connect a real, approved task/ad provider and verify completion using provider callbacks or signed server-to-server requests.
- Set real payout procedures and comply with local laws, tax, privacy, consumer-protection, and platform rules.
- Add rate limits, monitoring, backups, fraud review, and independent security testing.
- Never pay users merely because the browser sends `completed=true`.
- Do not put bot tokens, database passwords, or admin secrets in frontend code.

## Requirements
- Docker Desktop / Docker Engine with Compose, OR Python 3.12+ and PostgreSQL 16+
- A Telegram bot created with `@BotFather`
- A public HTTPS URL for the Mini App (for example via a deployment host or HTTPS tunnel during development)

## Quick start (Docker)
1. Copy `.env.example` to `.env`.
2. Fill `BOT_TOKEN` and `ADMIN_TELEGRAM_IDS` (comma-separated numeric Telegram IDs).
3. Change `APP_SECRET` to a long random secret.
4. Run:
   ```bash
   docker compose up --build
   ```
5. API docs: `http://localhost:8000/docs`
6. Mini App: `http://localhost:8000/`
7. Admin panel: `http://localhost:8000/admin`

Localhost is for development only. Telegram Mini Apps require HTTPS when hosted publicly. Configure your BotFather Mini App URL to the deployed HTTPS URL.

## Telegram bot setup
1. In Telegram, open `@BotFather`, run `/newbot`, and copy the bot token.
2. Put it in `.env` as `BOT_TOKEN=...`.
3. Set the Mini App URL using BotFather's Mini App settings / menu button.
4. Run `python -m app.bot` locally (or use the included Docker service).
5. Add your Telegram numeric user ID to `ADMIN_TELEGRAM_IDS`.

## Production setup
- Deploy the app behind HTTPS.
- Use a managed PostgreSQL database or private network database.
- Set strong secrets and restrict database network access.
- Configure provider webhooks and signature verification for tasks.
- Use a real payout integration only after provider and legal requirements are reviewed.
- Use a persistent volume and scheduled encrypted backups.
- Review `SECURITY.md` before going live.

## Project structure
```
app/
  main.py       FastAPI API + frontend static hosting
  bot.py        aiogram bot / Mini App entry point
  config.py     environment configuration
  db.py         SQLAlchemy async database setup
  models.py     database models
  schemas.py    request/response schemas
  security.py   Telegram initData verification and admin checks
  services.py   ledger, tasks, referrals, withdrawals
  routes/
    users.py
    tasks.py
    referrals.py
    withdrawals.py
    admin.py
web/
  index.html
  app.js
  styles.css
  admin.html
  admin.js
  admin.css
.env.example
docker-compose.yml
Dockerfile
requirements.txt
```
