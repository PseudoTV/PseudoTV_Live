import os
import subprocess
import json
import requests

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_pr_diff():
    """Gets the raw git diff of the PR changes."""
    subprocess.run(["git", "fetch", "origin", "main"], check=True)
    result = subprocess.run(["git", "diff", "origin/main...HEAD"], capture_output=True, text=True, check=True)
    return result.stdout

def run_kodi_addon_checker():
    """Runs the official Team Kodi validation script via CLI."""
    print("Running Team Kodi Addon Checker...")
    # --allow-folder-id-mismatch handles generic workspace root folders smoothly
    # Adjust --branch parameter to match your target Kodi generation (omega, nexus, matrix, etc.)
    cmd = ["kodi-addon-checker", "--branch", "omega", "--allow-folder-id-mismatch", "."]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # The checker uses exit codes to signify repo validation states, 
    # but we capture stdout/stderr to parse the structural feedback.
    return result.returncode == 0, result.stdout + result.stderr

def call_ai(system_prompt, user_content):
    """Placeholder function for your preferred LLM API call."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2
    }
    ai_headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=ai_headers)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI Generation Failed: {str(e)}"

def post_github_comment(body):
    """Posts a summary comment to the Pull Request."""
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    requests.post(url, json={"body": body}, headers=headers)

def main():
    print("Analyzing PR Changes...")
    diff = get_pr_diff()
    if not diff.strip():
        print("No changes detected.")
        return

    # --- PART 1: TEAM KODI OFFICIAL ADDON CHECKER ---
    checker_passed, checker_logs = run_kodi_addon_checker()
    checker_status_badge = "✅ PASS" if checker_passed else "⚠️ WARNINGS/ERRORS"

    # --- PART 2: AI LINTING / CODE REVIEW ---
    linter_prompt = (
        "You are an expert Kodi addon code linter and reviewer. Analyze the following git diff. "
        "Pay attention to Python 3 optimizations, complex UI dialog optimizations, memory leaks with WindowXML, "
        "improper database caching contexts, or common Kodi script bugs. "
        "Provide a concise, bulleted markdown summary of suggestions."
    )
    print("Running AI Code Review...")
    review_summary = call_ai(linter_prompt, diff)

    # --- PART 3: DYNAMIC TEST GENERATION ---
    test_gen_prompt = (
        "You are an expert QA automation engineer specializing in Python and Kodi mocking wrappers. "
        "Analyze the following git diff and write a functional python test file using pytest. "
        "Mock any 'xbmc', 'xbmcgui', or 'xbmcaddon' dependencies accurately using unittest.mock. "
        "Return ONLY the executable python code inside your response. Do not include markdown blocks."
    )
    print("Generating Dynamic Tests...")
    generated_test_code = call_ai(test_gen_prompt, diff)

    # Save the generated test to a temporary file
    test_file_path = "test_dynamic_ai.py"
    with open(test_file_path, "w") as f:
        f.write(generated_test_code)

    # Execute the dynamically generated tests
    print("Executing Generated Tests...")
    test_run = subprocess.run(["pytest", test_file_path], capture_output=True, text=True)
    
    if os.path.exists(test_file_path):
        os.remove(test_file_path)

    test_status = "✅ PASS" if test_run.returncode == 0 else "❌ FAIL"
    
    # --- PART 4: AGGREGATE COMPREHENSIVE REPORT ---
    final_report = f"""
### 🤖 Automated Code Quality & Testing Report

#### 📦 Official Kodi Addon Checker: **{checker_status_badge}**
```text
{checker_logs if checker_logs.strip() else "No structural errors found by the kodi-addon-checker validation schemas."}