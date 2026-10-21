import os,re
from flask import Flask,request,jsonify,send_from_directory
import requests

app=Flask(__name__,static_folder=".")
ENDPOINT="https://discord.com/api/v9/unique-username/username-attempt-unauthed"
RX=re.compile(r"^[a-z0-9._]+$")

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.post("/api/discord/check")
def check():
    body=request.get_json(silent=True) or {}
    username=body.get("username","")
    if not isinstance(username,str): return jsonify(status="invalid",verified=False,error="USERNAME_REQUIRED"),400
    username=username.strip().lower()
    if not 2<=len(username)<=32: return jsonify(status="invalid",verified=True,username=username,error="INVALID_LENGTH"),400
    if not RX.fullmatch(username): return jsonify(status="invalid",verified=True,username=username,error="INVALID_CHARACTERS"),400
    if username.startswith(".") or username.endswith(".") or ".." in username:
        return jsonify(status="invalid",verified=True,username=username,error="INVALID_PERIODS"),400
    try:
        r=requests.post(ENDPOINT,json={"username":username},headers={
            "Content-Type":"application/json","Accept":"application/json",
            "User-Agent":"DiscordUsernameChecker/1.0"
        },timeout=15)
    except requests.RequestException as e:
        return jsonify(status="server_error",verified=False,error="DISCORD_REQUEST_FAILED"),502
    try: data=r.json()
    except Exception: data=None
    if r.status_code==429:
        return jsonify(status="rate_limited",verified=False,username=username,retryAfter=r.headers.get("retry-after")),429
    if r.status_code==200 and isinstance(data,dict) and isinstance(data.get("taken"),bool):
        return jsonify(status="taken" if data["taken"] else "available",taken=data["taken"],verified=True,username=username)
    if r.status_code in (400,422):
        return jsonify(status="invalid",verified=True,username=username,discord=data),400
    return jsonify(status="discord_error",verified=False,username=username,discordStatus=r.status_code,discordResponse=data),502

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","8080")))
