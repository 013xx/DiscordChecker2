# DiscordChecker2

Flat Cloudflare Worker repository.

Files:
- index.html
- worker.js
- wrangler.jsonc
- .gitignore

Cloudflare Workers Builds:
- Root: /
- Build command: empty
- Deploy command: npx wrangler deploy

The Worker calls Discord's unauthenticated username-attempt endpoint and only marks a result VERIFIED when Discord returns a boolean `taken` field.
