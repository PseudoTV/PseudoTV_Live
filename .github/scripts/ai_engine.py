import os
import subprocess
import requests
import sys

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPO = os.getenv("GITHUB_REPOSITORY", "PseudoTV/PseudoTV_Live")
PR_NUMBER = os.getenv("PR_NUMBER")
GITHUB_BASE_REF = os.getenv("GITHUB_BASE_REF")
FULL_EVAL = os.getenv("FULL_EVAL", "false").lower() == "true"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_pr_diff():
    base_branch = GITHUB_BASE_REF or "nightly"
    subprocess.run(["git", "fetch", "origin", base_branch], capture_output=True, text=True)
    for target in [f"origin/{base_branch}", base_branch, "HEAD~1"]:
        result = subprocess.run(["git", "diff", f"{target}...HEAD"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    return ""

def get_full_project_code():
    codebase = ""
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith((".py",".xml",".json")) and "test" not in file and "scripts" not in root:
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        codebase += f"\n\n--- FILE: {path} ---\n" + f.read()
                except Exception: continue
    return codebase

def run_kodi_addon_checker():
    cmd = ["kodi-addon-checker", "--branch", "omega", "plugin.video.pseudotv.live"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = result.stdout.splitlines()
    
    errors = [line.replace("ERROR:", "❌ **[ERROR]**") for line in lines if line.startswith("ERROR:")]
    warnings = [line.replace("WARN:", "⚠️ **[WARN]**") for line in lines if line.startswith("WARN:")]
    
    combined = errors + warnings
    formatted_logs = "\n".join([f"• {line}" for line in combined]) if combined else "✅ **No issues detected!**"
    return result.returncode == 0, formatted_logs

def validate_and_rank_keys(raw_keys_str):
    if not raw_keys_str: return []
    valid_keys = []
    raw_keys = [k.strip() for k in raw_keys_str.replace(";", ",").split(",") if k.strip()]
    for key in raw_keys:
        try:
            res = requests.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"}, timeout=8)
            if res.status_code == 200:
                valid_keys.append({"key": key, "label": res.json().get("data", {}).get("label", "Key")})
        except Exception: continue
    return valid_keys

def call_ai_smart(system_prompt, user_content, valid_keys):
    url = "https://openrouter.ai/api/v1/chat/completions"
    key = valid_keys[0]["key"] if valid_keys else (OPENROUTER_API_KEY or "no_key")
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2
    }
    try:
        res = requests.post(url, json=payload, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, timeout=60)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'], "Success"
        return f"❌ **API Error:** Received {res.status_code}", "Failed"
    except Exception as e:
        return f"❌ **Request Error:** {e}", "Failed"

def post_github_comment(body):
    if not PR_NUMBER or PR_NUMBER == "None" or not GITHUB_TOKEN:
        print(body)
        return
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    requests.post(url, json={"body": body}, headers=headers)

def main():
    eval_content = get_full_project_code() if FULL_EVAL else get_pr_diff()
    scope_label = "Full Project" if FULL_EVAL else "PR Diff"
    
    checker_passed, checker_logs = run_kodi_addon_checker()
    checker_status = "✅ PASS" if checker_passed else "❌ FAIL"
    valid_keys = validate_and_rank_keys(OPENROUTER_API_KEY)
    
    # Enhanced Review Prompt
    linter_prompt = (
        "Expert Kodi developer. Analyze Content for changes, recommend improvements or optimizations that will improve the project. Review Checker the output of kodi-addon-checker for insight. Output formatted markdown using ASCII art headers (e.g., '### 📂 Analysis') "
        "and emoji lists (🚀, 💡, 🐛, ✅). Keep it high-impact and readable."
    )
    review_summary, _ = call_ai_smart(linter_prompt, f"Content: {eval_content}\nChecker: {checker_logs}", valid_keys)
    
    # Restored Markdown for test generation so the AI provides code blocks
    test_gen_prompt = "Write a pytest file. Use sys.path to add 'resources/lib'. Mock xbmc modules to simulate xbmc kodi api. Use Markdown code blocks."
    generated_test_code, _ = call_ai_smart(test_gen_prompt, eval_content, valid_keys)
    
    test_file_path = "test_dynamic_ai.py"
    test_status = "⚠️ SKIPPED"
    test_output = "No tests were executed."
    
    # Extract code from markdown block if provided by AI
    clean_code = generated_test_code.split("```python")[-1].split("```")[0] if "```" in generated_test_code else generated_test_code
    
    if checker_passed and "Error" not in generated_test_code and clean_code.strip():
        with open(test_file_path, "w") as f: f.write(clean_code)
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{os.getcwd()}:{os.getcwd()}/resources/lib"
        test_run = subprocess.run(["pytest", test_file_path], env=env, capture_output=True, text=True)
        
        test_status = "✅ PASS" if test_run.returncode == 0 else "❌ FAIL"
        test_output = f"```bash\n{test_run.stdout + test_run.stderr}\n```"
        if os.path.exists(test_file_path): os.remove(test_file_path)

    # Final Formatted Report
    final_report = (
        f"### 🤖 **Automated Quality Engine**\n"
        f"**Scope:** `{scope_label}`\n\n"
        "--- 📦 **KODI CHECKER** ---\n"
        f"Status: {checker_status}\n\n"
        f"{checker_logs}\n\n"
        "--- 🧠 **CODE REVIEW** ---\n"
        f"{review_summary}\n\n"
        "--- 🧪 **DYNAMIC TEST SUITE** ---\n"
        f"Result: {test_status}\n\n"
        f"<details><summary>🔬 Click to reveal test diagnostic logs</summary>\n\n"
        f"{test_output}\n"
        "</details>"
    )
    post_github_comment(final_report)

if __name__ == "__main__":
    main()