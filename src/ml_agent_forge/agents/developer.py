"""Developer (Coder) agent: generates Python code, runs it in E2B sandbox, self-corrects on error."""

import os
import base64
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from structlog import get_logger
from langchain_core.messages import HumanMessage, SystemMessage
from e2b_code_interpreter import Sandbox

from src.ml_agent_forge.state import GraphState
from src.ml_agent_forge.utils.logger import truncate_for_log

MAX_CORRECTION_ATTEMPTS = 3
SANDBOX_DATA_DIR = "/home/user/data"
SANDBOX_ARTIFACTS_DIR = "/home/user/artifacts"


def _get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")
    return ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=api_key, temperature=0)


def _create_sandbox():
    """Create E2B Code Interpreter sandbox (uses E2B_API_KEY from env)."""
    if not os.getenv("E2B_API_KEY"):
        raise ValueError("E2B_API_KEY must be set in environment")
    return Sandbox.create()


def _upload_user_files(sandbox: Sandbox, file_paths: list[str]) -> list[str]:
    """Upload local files to sandbox under SANDBOX_DATA_DIR; return list of sandbox paths."""
    sandbox_paths = []
    for fp in file_paths or []:
        path = Path(fp)
        if not path.exists():
            continue
        name = path.name
        sandbox_path = f"{SANDBOX_DATA_DIR}/{name}"
        with open(path, "rb") as f:
            sandbox.files.write(sandbox_path, f.read())
        sandbox_paths.append(sandbox_path)
    return sandbox_paths


def _ensure_artifacts_dir(sandbox: Sandbox) -> None:
    """Ensure artifacts directory exists in sandbox via run_code."""
    sandbox.run_code(f"import os; os.makedirs({SANDBOX_ARTIFACTS_DIR!r}, exist_ok=True)")


def _run_code_in_sandbox(sandbox: Sandbox, code: str, timeout: float = 120.0):
    """Execute Python code in sandbox; return (stdout, stderr, results, error)."""
    exec_result = sandbox.run_code(code, timeout=timeout)
    stdout = "\n".join(exec_result.logs.stdout) if exec_result.logs else ""
    stderr = "\n".join(exec_result.logs.stderr) if exec_result.logs else ""
    results = []
    if exec_result.results:
        for r in exec_result.results:
            results.append({"text": r.text, "png_base64": getattr(r, "_repr_png", lambda: None)()})
    err = exec_result.error
    return stdout, stderr, results, err


def _collect_artifact_files(sandbox: Sandbox) -> list[dict]:
    """List and read artifact files from SANDBOX_ARTIFACTS_DIR; return list of {path, content_base64, mime}."""
    artifacts = []
    try:
        exec_res = sandbox.run_code(
            f"import os; "
            f"names = os.listdir({SANDBOX_ARTIFACTS_DIR!r}) if os.path.isdir({SANDBOX_ARTIFACTS_DIR!r}) else []; "
            f"print('\\n'.join(names))"
        )
        names_str = ""
        if exec_res.logs and exec_res.logs.stdout:
            names_str = "\n".join(exec_res.logs.stdout)
        if not names_str and exec_res.text:
            names_str = exec_res.text
        if not names_str:
            return artifacts
        names = [n.strip() for n in names_str.split("\n") if n.strip()]
        for name in names:
            if name in (".", ".."):
                continue
            path = f"{SANDBOX_ARTIFACTS_DIR}/{name}"
            try:
                try:
                    data = sandbox.files.read(path, format="bytes")
                except TypeError:
                    data = sandbox.files.read(path)
                if data is None:
                    data = b""
                if isinstance(data, str):
                    data = data.encode("utf-8")
                b64 = base64.b64encode(data).decode("ascii") if data else ""
                ext = Path(name).suffix.lower()
                mime = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "application/octet-stream"
                artifacts.append({"path": path, "content_base64": b64, "mime": mime})
            except Exception:
                continue
    except Exception:
        pass
    return artifacts


def developer_node(state: GraphState) -> dict:
    """Generate code from plan, run in E2B sandbox, capture outputs and artifacts; self-correct up to 3 times."""
    user_input = state.get("user_input") or {}
    data_profile = state.get("data_profile") or ""
    plan = state.get("plan") or ""
    code_context = list(state.get("code_context") or [])
    file_paths = user_input.get("file_paths") or []
    task = user_input.get("task", "")
    get_logger().info(
        "Agent started",
        agent="Developer",
        task=task[:200] + "..." if len(task) > 200 else task,
        plan_len=len(plan),
        code_context_entries=len(code_context),
    )

    try:
        with _create_sandbox() as sandbox:
            sandbox_paths = _upload_user_files(sandbox, file_paths)
            _ensure_artifacts_dir(sandbox)

            system_prompt = """
You are an expert Python developer for data analysis and ML. Rules:
- Output only valid, runnable Python code. No markdown fences or explanations around the code.
- Use pandas and numpy. Data files are in /home/user/data/ (paths provided below).
- Save all charts/figures to disk under /home/user/artifacts/ (e.g. plt.savefig('/home/user/artifacts/fig1.png')).
- Use strict Python syntax. Avoid interactive backends; use 'Agg' for matplotlib if needed.
- Print key results (metrics, shapes) so they appear in stdout."""

            code_prompt = f"""
Plan to implement:
{plan}

Data profile (for reference):
{data_profile}

Data file paths inside sandbox (use these in pd.read_csv etc.):
{sandbox_paths}

Generate a single Python script that implements the plan. Save plots to /home/user/artifacts/. Output only the code."""

            last_error = None
            last_code = None
            stdout, stderr, results, err = "", "", [], None

            for attempt in range(MAX_CORRECTION_ATTEMPTS):
                llm = _get_llm()
                if attempt == 0:
                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=code_prompt),
                    ]
                else:
                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=code_prompt),
                        HumanMessage(content=f"Previous code failed. Error:\n{last_error}\n\nProvide corrected code only."),
                    ]
                full_prompt = code_prompt + (f"\n\n[Correction request: {last_error}]" if attempt > 0 else "")
                get_logger().debug(
                    "LLM invoke (Developer)",
                    agent="Developer",
                    attempt=attempt + 1,
                    prompt_truncated=truncate_for_log(full_prompt, 800),
                )
                response = llm.invoke(messages)
                raw = response.content if hasattr(response, "content") else str(response)
                get_logger().info(
                    "LLM response (Developer)",
                    agent="Developer",
                    attempt=attempt + 1,
                    code_truncated=truncate_for_log(raw, 500),
                )
                code = raw.strip()
                if code.startswith("```"):
                    lines = code.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    code = "\n".join(lines)
                last_code = code

                stdout, stderr, results, err = _run_code_in_sandbox(sandbox, code)
                if err is None:
                    break
                last_error = f"{getattr(err, 'value', err)}" if err else "Unknown error"

            artifacts = _collect_artifact_files(sandbox)

            entry = {
                "code": last_code,
                "stdout": stdout,
                "stderr": stderr,
                "results": results,
                "artifacts": artifacts,
                "error": None if err is None else str(getattr(err, "value", err)),
            }
            code_context = code_context + [entry]

    except Exception as e:
        return {
            "code_context": code_context + [{"error": f"Sandbox/file upload failed: {e!s}", "code": None}],
            "messages": (state.get("messages") or []) + [HumanMessage(content=f"Developer failed: {e!s}")],
        }

    return {
        "code_context": code_context,
        "messages": (state.get("messages") or []) + [HumanMessage(content="Developer ran code in E2B sandbox.")],
    }
