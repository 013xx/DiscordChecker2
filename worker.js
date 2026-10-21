const DISCORD_ENDPOINT =
  "https://discord.com/api/v9/unique-username/username-attempt-unauthed";

const USERNAME_REGEX = /^[a-z0-9._]+$/;

function reply(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Access-Control-Allow-Origin": "*"
    }
  });
}

async function discordCheck(username) {
  const response = await fetch(DISCORD_ENDPOINT, {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      "Origin": "https://discord.com",
      "Referer": "https://discord.com/",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/136.0.0.0 Safari/537.36"
    },
    body: JSON.stringify({ username }),
    redirect: "follow"
  });

  const raw = await response.text();

  let data = null;
  try { data = JSON.parse(raw); } catch {}

  if (response.status === 429) {
    return reply({
      status: "rate_limited",
      verified: false,
      username,
      retryAfter:
        response.headers.get("retry-after") ||
        response.headers.get("x-ratelimit-reset-after")
    }, 429);
  }

  if (response.ok && data && typeof data.taken === "boolean") {
    return reply({
      status: data.taken ? "taken" : "available",
      taken: data.taken,
      verified: true,
      username
    });
  }

  if (response.status === 400 || response.status === 422) {
    return reply({
      status: "invalid",
      verified: true,
      username,
      discord: data || raw.slice(0, 500)
    }, 400);
  }

  // Diagnostic information instead of silently showing UNVERIFIED.
  return reply({
    status: "discord_error",
    verified: false,
    username,
    discordStatus: response.status,
    discordResponse: data || raw.slice(0, 500)
  }, 502);
}

async function handleCheck(request) {
  if (request.method !== "POST") {
    return reply({ error: "METHOD_NOT_ALLOWED" }, 405);
  }

  try {
    const body = await request.json();
    const username =
      typeof body?.username === "string"
        ? body.username.trim().toLowerCase()
        : "";

    if (!username) {
      return reply({
        status: "invalid",
        verified: false,
        error: "USERNAME_REQUIRED"
      }, 400);
    }

    if (username.length < 2 || username.length > 32) {
      return reply({
        status: "invalid",
        verified: true,
        username,
        error: "INVALID_LENGTH"
      }, 400);
    }

    if (!USERNAME_REGEX.test(username)) {
      return reply({
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
      return reply({
        status: "invalid",
        verified: true,
        username,
        error: "INVALID_PERIODS"
      }, 400);
    }

    return await discordCheck(username);
  } catch (error) {
    return reply({
      status: "server_error",
      verified: false,
      error: "REQUEST_FAILED",
      detail: String(error?.message || error)
    }, 500);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/discord/check") {
      return handleCheck(request);
    }

    // CORS preflight, if the endpoint is tested from another frontend.
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type"
        }
      });
    }

    return env.ASSETS.fetch(request);
  }
};
