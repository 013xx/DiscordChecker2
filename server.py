from flask import Flask, request, jsonify, send_from_directory
import requests
import re
import os
import logging

app = Flask(__name__, static_folder=".", static_url_path="")

# --------------------------------------------------
# Configuration
# --------------------------------------------------

DISCORD_URL = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8080))

REQUEST_TIMEOUT = 15

# Discord username rules
USERNAME_PATTERN = re.compile(r"^[a-z0-9._]+$")


# --------------------------------------------------
# Logging
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# CORS
# --------------------------------------------------

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "server": "DiscordChecker2",
        "discord": "connected endpoint ready"
    }), 200


# --------------------------------------------------
# Main Discord checker
# --------------------------------------------------

@app.route("/api/discord/check", methods=["POST", "OPTIONS"])
def check_username():

    # Browser CORS preflight
    if request.method == "OPTIONS":
        return "", 204

    # Make sure JSON was actually sent
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request must contain JSON."
        }), 400

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid JSON body."
        }), 400

    username = data.get("username")

    # Make sure username exists
    if not isinstance(username, str):
        return jsonify({
            "success": False,
            "error": "Username is required."
        }), 400

    username = username.strip()

    # --------------------------------------------------
    # Username validation
    # --------------------------------------------------

    if len(username) < 2 or len(username) > 32:
        return jsonify({
            "success": False,
            "status": "invalid",
            "error": "Username must be between 2 and 32 characters."
        }), 400

    # Discord usernames are lowercase
    if username != username.lower():
        return jsonify({
            "success": False,
            "status": "invalid",
            "error": "Username must use lowercase characters."
        }), 400

    if not USERNAME_PATTERN.fullmatch(username):
        return jsonify({
            "success": False,
            "status": "invalid",
            "error": "Username contains invalid characters."
        }), 400

    # Discord does not allow periods at the beginning/end
    if username.startswith(".") or username.endswith("."):
        return jsonify({
            "success": False,
            "status": "invalid",
            "error": "Username cannot start or end with a period."
        }), 400

    # Discord does not allow consecutive periods
    if ".." in username:
        return jsonify({
            "success": False,
            "status": "invalid",
            "error": "Username cannot contain consecutive periods."
        }), 400

    # --------------------------------------------------
    # Discord request
    # --------------------------------------------------

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        )
    }

    payload = {
        "username": username
    }

    try:
        logger.info("Checking Discord username: %s", username)

        response = requests.post(
            DISCORD_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(
            "Discord response: HTTP %s",
            response.status_code
        )

    except requests.exceptions.Timeout:
        logger.error("Discord request timed out.")

        return jsonify({
            "success": False,
            "status": "timeout",
            "error": "Discord request timed out."
        }), 504

    except requests.exceptions.ConnectionError:
        logger.exception("Could not connect to Discord.")

        return jsonify({
            "success": False,
            "status": "connection_error",
            "error": "Could not connect to Discord."
        }), 502

    except requests.exceptions.RequestException:
        logger.exception("Discord request failed.")

        return jsonify({
            "success": False,
            "status": "request_error",
            "error": "Discord request failed."
        }), 502

    # --------------------------------------------------
    # Discord response handling
    # --------------------------------------------------

    if response.status_code == 200:

        try:
            result = response.json()
        except ValueError:
            logger.error("Discord returned invalid JSON.")

            return jsonify({
                "success": False,
                "status": "invalid_response",
                "error": "Discord returned an invalid response."
            }), 502

        taken = result.get("taken")

        if isinstance(taken, bool):

            if taken:
                return jsonify({
                    "success": True,
                    "status": "taken",
                    "taken": True,
                    "available": False,
                    "username": username
                }), 200

            return jsonify({
                "success": True,
                "status": "available",
                "taken": False,
                "available": True,
                "username": username
            }), 200

        logger.error(
            "Discord returned HTTP 200 but no boolean 'taken' field."
        )

        return jsonify({
            "success": False,
            "status": "invalid_response",
            "error": "Discord returned an unexpected response."
        }), 502

    # Rate limited
    if response.status_code == 429:

        retry_after = response.headers.get("Retry-After")

        return jsonify({
            "success": False,
            "status": "rate_limited",
            "error": "Discord rate limited the checker.",
            "retry_after": retry_after
        }), 429

    # Invalid Discord request
    if response.status_code in (400, 422):

        return jsonify({
            "success": False,
            "status": "invalid",
            "error": "Discord rejected this username request."
        }), 400

    # Authentication / Cloudflare / blocking
    if response.status_code in (401, 403):

        logger.error(
            "Discord rejected the server request: HTTP %s",
            response.status_code
        )

        return jsonify({
            "success": False,
            "status": "discord_blocked",
            "error": (
                "Discord rejected the server request "
                f"(HTTP {response.status_code})."
            ),
            "discord_status": response.status_code
        }), 502

    # Discord unavailable
    if response.status_code >= 500:

        return jsonify({
            "success": False,
            "status": "discord_unavailable",
            "error": "Discord is currently unavailable.",
            "discord_status": response.status_code
        }), 502

    # Unknown response
    return jsonify({
        "success": False,
        "status": "discord_error",
        "error": "Unexpected Discord response.",
        "discord_status": response.status_code
    }), 502


# --------------------------------------------------
# Frontend
# --------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    return send_from_directory(".", "index.html")


# --------------------------------------------------
# Start server
# --------------------------------------------------

if __name__ == "__main__":

    logger.info("----------------------------------------")
    logger.info("DiscordChecker2 starting")
    logger.info("Host: %s", HOST)
    logger.info("Port: %s", PORT)
    logger.info("Health: /health")
    logger.info("Checker: /api/discord/check")
    logger.info("----------------------------------------")

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        threaded=True
    )
