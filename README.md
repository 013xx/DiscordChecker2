# Discord Checker — Cloudflare Worker

This is intentionally FLAT. There are no `functions/` or `api/` folders.

Files:
- `index.html` — website
- `worker.js` — Cloudflare Worker + Discord API proxy
- `wrangler.jsonc` — Worker configuration
- `.gitignore`

Cloudflare Workers Builds:
- Root directory: `/`
- Build command: leave blank
- Deploy command: `npx wrangler deploy`

Do NOT upload `node_modules`.

The Worker serves the website through the Assets binding and handles:
POST /api/discord/check
