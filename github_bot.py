import os
import requests
import hmac
import hashlib
import re
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configure Gemini
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    print(f"Failed to initialize Gemini: {e}")

GITHUB_TOKEN = os.environ.get("GITHUB_PUPBOT_TOKEN")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")

def verify_signature(payload_body, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256 HMAC."""
    if not GITHUB_WEBHOOK_SECRET:
        # In production, this should be mandatory. For now, we warn.
        print("Warning: GITHUB_WEBHOOK_SECRET not set. Skipping signature verification.")
        return True

    if not signature_header:
        return False

    hash_object = hmac.new(GITHUB_WEBHOOK_SECRET.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)

@app.route("/", methods=["GET"])
def index():
    return "Codepup GitHub Webhook is listening! Arf!"

def perform_review(pr_number, diff_url_or_api, repo_full_name, use_api_header=False):
    # Security: Validate GitHub URLs to prevent SSRF
    allowed_prefixes = ("https://api.github.com/", "https://github.com/")
    if not any(diff_url_or_api.startswith(prefix) for prefix in allowed_prefixes):
        print(f"Aborting: diff_url_or_api '{diff_url_or_api}' does not start with an allowed GitHub prefix.")
        return False

    # Security: Validate repo_full_name format (owner/repo)
    if not re.match(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$", repo_full_name):
        print(f"Aborting: repo_full_name '{repo_full_name}' is invalid.")
        return False

    headers = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f"token {GITHUB_TOKEN}"
    if use_api_header:
        headers['Accept'] = 'application/vnd.github.v3.diff'
        
    diff_resp = requests.get(diff_url_or_api, headers=headers, timeout=(5, 30))
    if diff_resp.status_code != 200:
        print("Failed to get diff")
        return False
        
    diff_text = diff_resp.text
    
    prompt = f"""
    You are "Codepup", an elite AI code review assistant (superior to CodeRabbit).
    You are a highly capable senior developer with a playful pup persona, but extremely serious about code quality.
    Your goal is to review the following git diff and output a world-class code review.

    Guidelines:
    1. **Summary**: Provide a bulleted summary of what changed.
    2. **Issues & Bugs**: Point out any logical bugs, security flaws, resource leaks, or edge cases. If none exist, praise the code!
    3. **Performance & Best Practices**: Suggest optimizations or cleaner patterns. Avoid nitpicks (e.g. trailing whitespaces).
    4. **Provide Fixes**: IMPORTANT - If you find an issue, provide the EXACT code fix using Github code suggestion markdown format (i.e. ` ```suggestion `) or standard diff blocks so the developer can easily copy/paste or apply it.

    Keep the tone encouraging, elite, and slightly playful (maybe one 'Arf!' or tail wag compliment). 

    Here is the diff:
    {diff_text}
    """
    try:
        print(f"Analyzing PR #{pr_number} with Codepup (Gemini)...")
        ai_response = model.generate_content(prompt)
        review_comment = f"🐶 **Codepup Review** 🐾\n\n{ai_response.text}"
        
        if GITHUB_TOKEN:
            comment_url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
            # Remove the Accept header for posting the comment
            post_headers = {'Authorization': f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
            res = requests.post(comment_url, headers=post_headers, json={"body": review_comment}, timeout=(5, 30))
            if res.status_code == 201:
                print(f"Successfully posted review to PR #{pr_number}")
                return True
            else:
                print(f"Failed to post comment: {res.text}")
        else:
            print("Missing GITHUB_TOKEN! Could not post comment. Here is what Codepup generated:")
            print(review_comment)
    except Exception as e:
        print(f"Error executing Codepup code review: {e}")
    return False

@app.route("/github-webhook", methods=["POST"])
def github_webhook():
    signature = request.headers.get('X-Hub-Signature-256')
    payload_body = request.get_data()

    if not verify_signature(payload_body, signature):
        return jsonify({"error": "Invalid signature"}), 403

    event = request.headers.get('X-GitHub-Event')
    payload = request.json

    print(f"Received GitHub Webhook: {event}")

    # 1. Listen for new PRs or changes to a PR
    if event == "pull_request" and payload.get("action") in ["opened", "synchronize"]:
        pr = payload["pull_request"]
        diff_url = pr["diff_url"]
        repo_full_name = payload["repository"]["full_name"]
        pr_number = pr["number"]
        
        perform_review(pr_number, diff_url, repo_full_name)
        
    # 2. Listen for manual trigger via comments (@pupbot or /pupbot)
    elif event == "issue_comment" and payload.get("action") == "created":
        comment_body = payload["comment"]["body"].lower()
        if ("@pupbot review" in comment_body or "/pupbot" in comment_body or "/review" in comment_body or "@gemini" in comment_body or "gemini" in comment_body) and "pull_request" in payload["issue"]:
            pr_number = payload["issue"]["number"]
            repo_full_name = payload["repository"]["full_name"]
            pr_api_url = payload["issue"]["pull_request"]["url"]
            print(f"Manual Codepup review triggered via comment on PR #{pr_number}")
            # For PR API URLs, we must send the V3 diff accept header
            perform_review(pr_number, pr_api_url, repo_full_name, use_api_header=True)

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Heroku automatically injects the PORT variable for the web process
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Codepup GitHub Webhook Server on port {port}...")
    app.run(host='0.0.0.0', port=port)
