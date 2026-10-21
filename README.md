# DiscordChecker2 — static-egress backend

The previous Cloudflare Worker received HTTP 403 from Discord. This version moves the Discord request to a normal server process so its outbound IP can be controlled.

Files:
- index.html
- server.py
- requirements.txt
- Dockerfile
- README.md

IMPORTANT:
Cloudflare Worker shared egress is not used for the Discord request here. Deploy `server.py` on a VPS/server with an IP you control. Put the resulting public HTTPS URL into your frontend/proxy if desired.

Run locally:
python -m pip install -r requirements.txt
python server.py

Then open http://localhost:8080
