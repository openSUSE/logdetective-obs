import os
import re
import hmac
import hashlib
import requests
from flask import Flask, request, abort

app = Flask(__name__)

GITEA_TOKEN = os.getenv("GITEA_TOKEN")
GITEA_API_URL = "https://src.opensuse.org/api/v1"
GITEA_WEBHOOK_SECRET = os.getenv("GITEA_WEBHOOK_SECRET")

LOGDETECTIVE_API = "https://logdetective.com/frontend/explain"
BOT_USERNAME = "ai-logcheck"

def verify_signature(payload, signature):
    mac = hmac.new(GITEA_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature)

def post_pr_comment(owner, repo, pr_number, text):
    url = f"{GITEA_API_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {GITEA_TOKEN}"}
    r = requests.post(url, json={"body": text}, headers=headers)
    r.raise_for_status()

def call_logdetective(log_url):
    r = requests.post(LOGDETECTIVE_API, json={"log_url": log_url})
    r.raise_for_status()
    return r.json().get("explanation", "No explanation found.")

@app.route("/gitea-webhook", methods=["POST"])
def gitea_webhook():
    signature = request.headers.get("X-Gitea-Signature", "")
    if not verify_signature(request.data, signature):
        abort(403)

    event_type = request.headers.get("X-Gitea-Event", "")
    payload = request.json

    if event_type != "issue_comment":
        return "Ignored", 200
    if "pull_request" not in payload.get("issue", {}):
        return "Ignored", 200

    comment_body = payload["comment"]["body"].strip()
    comment_author = payload["comment"]["user"]["login"]

    # Only respond if someone mentions @ai-logcheck
    if not comment_body.startswith(f"@{BOT_USERNAME}"):
        return "Ignored", 200

    # Expected format: @ai-logcheck: PROJECT PACKAGE REPO ARCH
    parts = comment_body.split(":")
    if len(parts) < 2:
        return "No command found", 200

    command = parts[1].strip()
    args = command.split()
    if len(args) != 4:
        return "Usage: @ai-logcheck: PROJECT PACKAGE REPO ARCH", 200

    project, package, repo, arch = args

    # Construct OBS log URL
    log_url = f"https://build.opensuse.org/public/build/{project}/{repo}/{arch}/{package}_log"
    explanation = call_logdetective(log_url)

    owner = payload["repository"]["owner"]["login"]
    repo_name = payload["repository"]["name"]
    pr_number = payload["issue"]["number"]

    post_pr_comment(owner, repo_name, pr_number, f"### LogDetective Explanation\n\n{explanation}")

    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000)
