import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configure Gemini
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-pro')
except Exception as e:
    print(f"Failed to initialize Gemini: {e}")

GITHUB_TOKEN = os.environ.get("GITHUB_PUPBOT_TOKEN")

@app.route("/", methods=["GET"])
def index():
    return "Codepup GitHub Webhook is listening! Arf!"

@app.route("/github-webhook", methods=["POST"])
def github_webhook():
    event = request.headers.get('X-GitHub-Event')
    payload = request.json

    print(f"Received GitHub Webhook: {event}")

    # Listen for new PRs or changes to a PR
    if event == "pull_request" and payload.get("action") in ["opened", "synchronize"]:
        pr = payload["pull_request"]
        diff_url = pr["diff_url"]
        repo_full_name = payload["repository"]["full_name"]
        pr_number = pr["number"]
        
        # 1. Fetch the raw Diff
        headers = {}
        if GITHUB_TOKEN:
            headers['Authorization'] = f"token {GITHUB_TOKEN}"
            
        diff_resp = requests.get(diff_url, headers=headers)
        if diff_resp.status_code != 200:
            print("Failed to get diff")
            return jsonify({"status": "error", "message": "Failed to get diff"}), 400
            
        diff_text = diff_resp.text
        
        # 2. Ask Gemini for Review & Autofix
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
            
            # 3. Post review back to GitHub
            if GITHUB_TOKEN:
                comment_url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
                res = requests.post(comment_url, headers=headers, json={"body": review_comment})
                if res.status_code == 201:
                    print(f"Successfully posted review to PR #{pr_number}")
                else:
                    print(f"Failed to post comment: {res.text}")
            else:
                print("Missing GITHUB_TOKEN! Could not post comment. Here is what Codepup generated:")
                print(review_comment)
                
        except Exception as e:
            print(f"Error executing Codepup code review: {e}")
            
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Heroku automatically injects the PORT variable for the web process
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Codepup GitHub Webhook Server on port {port}...")
    app.run(host='0.0.0.0', port=port)
