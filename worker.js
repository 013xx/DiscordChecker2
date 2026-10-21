const DISCORD_ENDPOINT =
  "https://discord.com/api/v9/unique-username/username-attempt-unauthed";

const USERNAME_REGEX = /^[a-z0-9._]+$/;

function json(data, status = 200) {
  return Response.json(data, {
    status,
    headers: { "Cache-Control": "no-store" }
  });
}

async function checkDiscord(username) {
  const response = await fetch(DISCORD_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "User-Agent": "Mozilla/5.0 DiscordUsernameChecker"
    },
    body: JSON.stringify({ username })
  });

  if (response.status === 429) {
    return json({
      status: "rate_limited",
      verified: false,
      username,
      retryAfter: response.headers.get("retry-after")
    }, 429);
  }

  if (response.status === 400 || response.status === 422) {
    let discord = null;
    try { discord = await response.json(); } catch {}
    return json({
      status: "invalid",
      verified: true,
      username,
      discord
    }, 400);
  }

  if (response.status === 401 || response.status === 403) {
    return json({
      status: "blocked",
      verified: false,
      username
    }, response.status);
  }

  if (response.status >= 500) {
    return json({
      status: "unknown",
      verified: false,
      username,
      discordStatus: response.status
    }, 502);
  }

  let data;
  try {
    data = await response.json();
  } catch {
    return json({
      status: "unknown",
      verified: false,
      username
    }, 502);
  }

  if (response.ok && typeof data.taken === "boolean") {
    return json({
      status: data.taken ? "taken" : "available",
      taken: data.taken,
      verified: true,
      username
    });
  }

  return json({
    status: "unknown",
    verified: false,
    username
  }, 502);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/discord/check") {
      if (request.method !== "POST") {
        return json({ error: "METHOD_NOT_ALLOWED" }, 405);
      }

      try {
        const body = await request.json();
        const username =
          typeof body?.username === "string"
            ? body.username.trim().toLowerCase()
            : "";

        if (!username) {
          return json({
            status: "invalid",
            verified: false,
            error: "USERNAME_REQUIRED"
          }, 400);
        }

        if (username.length < 2 || username.length > 32) {
          return json({
            status: "invalid",
            verified: true,
            username,
            error: "INVALID_LENGTH"
          }, 400);
        }

        if (!USERNAME_REGEX.test(username)) {
          return json({
            status: "invalid",
            verified: true,
            username,
            error: "INVALID_CHARACTERS"
          }, 400);
        }

        if (
          username.startsWith(".") ||
          username.endsWith(".") ||
          username.includes("..")
        ) {
          return json({
            status: "invalid",
            verified: true,
            username,
            error: "INVALID_PERIODS"
          }, 400);
        }

        return await checkDiscord(username);
      } catch (error) {
        console.error("Discord checker error:", error);
        return json({
          status: "unknown",
          verified: false,
          error: "DISCORD_REQUEST_FAILED"
        }, 500);
      }
    }

    // Everything else is served from the static assets directory.
    return env.ASSETS.fetch(request);
  }
};
