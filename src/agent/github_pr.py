import subprocess
from datetime import datetime
import httpx
from src.agent.config import settings
from src.agent.schemas import CrashContext, DiagnosisPlan


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def open_draft_pull_request(
    crash: CrashContext,
    relative_file_path: str,
    diagnosis: DiagnosisPlan,
) -> str:
    if not settings.github_token:
        raise ValueError("GITHUB_TOKEN is missing in .env")

    base_branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"fix/{crash.service_name}-{crash.error_type.lower()}-{timestamp}"

    try:
        # Create fix branch, commit only the patched file, and push
        run_git(["checkout", "-b", branch_name])
        run_git(["add", relative_file_path])
        run_git([
            "commit",
            "-m",
            f"fix({crash.service_name}): resolve {crash.error_type} in {crash.function_name}",
        ])
        run_git(["push", "-u", "origin", branch_name])

        # Open Draft PR via GitHub REST API
        pr_title = f"[Autonomous Fix] {crash.error_type} in {crash.service_name}"
        pr_body = (
            f"### Automated Incident Triage & Verified Patch\n\n"
            f"- **Service:** `{crash.service_name}`\n"
            f"- **Target File:** `{relative_file_path}` (line {crash.line_number})\n"
            f"- **Error:** `{crash.error_type}: {crash.error_message}`\n\n"
            f"### Root Cause Analysis\n{diagnosis.root_cause}\n\n"
            f"### Summary of Fix\n{diagnosis.proposed_fix_summary}\n\n"
            f"---\n"
            f"*Verified automatically against unit test suite before opening this Draft PR.*"
        )

        url = f"https://api.github.com/repos/{settings.github_repo}/pulls"
        headers = {
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {
            "title": pr_title,
            "body": pr_body,
            "head": branch_name,
            "base": base_branch,
            "draft": True,
        }

        response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
        response.raise_for_status()
        pr_url = response.json()["html_url"]
        print(f"[GitHub] Draft PR opened: {pr_url}")
        return pr_url

    finally:
        # Always return to the original working branch
        run_git(["checkout", base_branch])