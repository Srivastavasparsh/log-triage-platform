import ast
import os
from pathlib import Path
from typing import TypedDict

from google import genai
from google.genai import types
from langgraph.graph import END, START, StateGraph

from src.agent.config import settings
from src.agent.github_pr import open_draft_pull_request
from src.agent.sandbox import run_tests_in_sandbox
from src.agent.schemas import CrashContext, DiagnosisPlan


class AgentState(TypedDict):
    crash: CrashContext
    relative_file_path: str
    original_code: str
    diagnosis: DiagnosisPlan | None
    test_passed: bool
    test_output: str
    attempts: int
    pr_url: str


def load_broken_file(state: AgentState) -> dict:
    raw_path = Path(state["crash"].file_path)
    relative_path = os.path.relpath(raw_path, Path.cwd())
    source_code = Path(relative_path).read_text(encoding="utf-8")

    return {
        "relative_file_path": relative_path,
        "original_code": source_code,
        "attempts": 0,
        "test_passed": False,
        "test_output": "",
        "pr_url": "",
    }


def diagnose_and_patch(state: AgentState) -> dict:
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    crash = state["crash"]
    current_attempt = state["attempts"] + 1

    target_path = Path(state["relative_file_path"])
    test_path = target_path.parent / f"test_{target_path.name}"
    test_code = test_path.read_text(encoding="utf-8") if test_path.exists() else ""

    retry_feedback = ""
    if state["test_output"]:
        retry_feedback = (
            f"\nPrevious patch failed verification tests:\n{state['test_output']}\n"
            "Fix the issue based on this test output."
        )

    prompt = (
        f"You are an on-call senior backend engineer.\n"
        f"Service: {crash.service_name}\n"
        f"Error: {crash.error_type}: {crash.error_message}\n"
        f"File: {state['relative_file_path']} (line {crash.line_number} in {crash.function_name})\n\n"
        f"Stack Trace:\n{crash.stack_trace}\n\n"
        f"Current Source Code:\n```python\n{state['original_code']}\n```\n\n"
        f"Existing Unit Tests (must pass):\n```python\n{test_code}\n```\n"
        f"{retry_feedback}\n\n"
        "Requirements:\n"
        "1. Return the complete, properly formatted multi-line Python file using standard newline characters (\\n).\n"
        "2. Do NOT squash code onto a single line.\n"
        "3. Preserve existing logging and function signatures so all unit tests pass."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DiagnosisPlan,
            temperature=0.1,
        ),
    )

    plan = DiagnosisPlan.model_validate_json(response.text)
    print(f"[Attempt {current_attempt}] Diagnosis: {plan.root_cause}")

    return {
        "diagnosis": plan,
        "attempts": current_attempt,
    }


def apply_and_verify(state: AgentState) -> dict:
    target_path = Path(state["relative_file_path"])
    plan = state["diagnosis"]

    try:
        ast.parse(plan.patched_code)
    except SyntaxError as exc:
        print(f"[Failed] Invalid Python syntax on attempt {state['attempts']}: {exc}")
        return {
            "test_passed": False,
            "test_output": f"SyntaxError in generated code: {exc}",
        }

    # Write candidate patch to disk for test verification
    target_path.write_text(plan.patched_code, encoding="utf-8")

    test_file = str(target_path.parent / f"test_{target_path.name}")
    passed, output = run_tests_in_sandbox(test_file)

    if passed:
        print(f"[Verified] All tests passed on attempt {state['attempts']}.")
    else:
        print(f"[Failed] Tests failed on attempt {state['attempts']}.")
        # Restore original file before retrying or exiting
        target_path.write_text(state["original_code"], encoding="utf-8")

    return {
        "test_passed": passed,
        "test_output": output,
    }


def create_pr(state: AgentState) -> dict:
    pr_url = open_draft_pull_request(
        crash=state["crash"],
        relative_file_path=state["relative_file_path"],
        diagnosis=state["diagnosis"],
    )
    return {"pr_url": pr_url}


def should_retry(state: AgentState) -> str:
    if state["test_passed"]:
        return "create_pr"
    if state["attempts"] >= settings.max_retries:
        print("[Escalated] Max retries reached without passing tests.")
        return END
    return "diagnose_and_patch"


def build_devops_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("load_broken_file", load_broken_file)
    workflow.add_node("diagnose_and_patch", diagnose_and_patch)
    workflow.add_node("apply_and_verify", apply_and_verify)
    workflow.add_node("create_pr", create_pr)

    workflow.add_edge(START, "load_broken_file")
    workflow.add_edge("load_broken_file", "diagnose_and_patch")
    workflow.add_edge("diagnose_and_patch", "apply_and_verify")
    workflow.add_conditional_edges("apply_and_verify", should_retry)
    workflow.add_edge("create_pr", END)

    return workflow.compile()