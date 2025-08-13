import os
import re
import requests
from flask import Flask, request, abort

app = Flask(__name__)


GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")  # Personal Access Token or Bot Token goes here
GITLAB_API_URL = "https://gitlab.example.com/api/v4"
GITLAB_WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET") # The webhook secret goes here

LOGDETECTIVE_API = "https://logdetective.com/explain"

def post_mr_comment(project_id, mr_iid, text):
    """Post a comment on a merge request."""
    url = f"{GITLAB_API_URL}/projects/{project_id}/merge_requests/{mr_iid}/notes"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    r = requests.post(url, json={"body": text}, headers=headers)
    r.raise_for_status()

def call_logdetective(log_url):
    """Send log URL to LogDetective API and get explanation."""
    r = requests.post(LOGDETECTIVE_API, json={"log_url": log_url})
    r.raise_for_status()
    return r.json().get("explanation", "No explanation found.")

@app.route("/gitlab-webhook", methods=["POST"])
def gitlab_webhook():
    # Verify secret
    token = request.headers.get("X-Gitlab-Token", "")
    if token != GITLAB_WEBHOOK_SECRET:
        abort(403)

    event_type = request.headers.get("X-Gitlab-Event", "")
    payload = request.json

    # Only handle note events on Merge Requests
    if event_type != "Note Hook":
        return "Ignored", 200
    if payload.get("object_attributes", {}).get("noteable_type") != "MergeRequest":
        return "Ignored", 200

    comment_body = payload["object_attributes"]["note"]
    comment_author = payload["user"]["username"]

    if comment_author == "autogits_obs_staging_bot" and "Build failed" in comment_body:
        # Extract log link
        match = re.search(r"https?://\S+\.log", comment_body)
        if not match:
            return "No log link found", 200

        log_url = match.group(0)
        explanation = call_logdetective(log_url)

        project_id = payload["project"]["id"]
        mr_iid = payload["merge_request"]["iid"]

        post_mr_comment(project_id, mr_iid, f"### LogDetective Explanation\n\n{explanation}")

    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000)
