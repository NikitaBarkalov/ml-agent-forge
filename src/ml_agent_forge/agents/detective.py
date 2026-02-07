"""DataDetective agent: analyzes input files and produces data_profile."""

import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.ml_agent_forge.state import GraphState


def _get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")
    return ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=api_key, temperature=0)


def _analyze_file(file_path: str) -> str:
    """Inspect a single file: CSV/Excel -> head, dtypes, summary; other -> type note."""
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _profile_csv(file_path)
    if suffix in (".xlsx", ".xls"):
        return _profile_excel(file_path)
    if suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".wav", ".mp3", ".ogg"):
        return f"File: {file_path} (type: {suffix[1:]}) — placeholder for future multimodal analysis."
    return f"File: {file_path} (unknown type) — no profile generated."


def _profile_csv(file_path: str) -> str:
    """Load first 5 rows, dtypes, and basic stats for a CSV."""
    try:
        import pandas as pd

        df = pd.read_csv(file_path, nrows=100)
        head = df.head(5).to_string()
        dtypes = df.dtypes.to_string()
        summary = df.describe(include="all").to_string() if len(df) > 0 else "(no rows)"
        return f"CSV: {file_path}\n--- head (5 rows) ---\n{head}\n--- dtypes ---\n{dtypes}\n--- describe ---\n{summary}"
    except Exception as e:
        return f"CSV {file_path} error: {e!s}"


def _profile_excel(file_path: str) -> str:
    """Load first sheet, first 5 rows and dtypes for an Excel file."""
    try:
        import pandas as pd

        xl = pd.ExcelFile(file_path)
        parts = [f"Excel: {file_path}, sheets: {xl.sheet_names}"]
        df = pd.read_excel(file_path, sheet_name=0)
        parts.append("--- head (5) ---")
        parts.append(df.head(5).to_string())
        parts.append("--- dtypes ---")
        parts.append(df.dtypes.to_string())
        return "\n".join(parts)
    except Exception as e:
        return f"Excel {file_path} error: {e!s}"


def detective_node(state: GraphState) -> dict:
    """Analyze files from user_input['file_paths'] and set data_profile."""
    user_input = state.get("user_input") or {}
    file_paths = user_input.get("file_paths") or []
    if not file_paths:
        profile = "No file paths provided."
    else:
        profiles = [_analyze_file(p) for p in file_paths]
        profile = "\n\n".join(profiles)

    return {
        "data_profile": profile,
        "messages": (state.get("messages") or []) + [
            HumanMessage(content=f"DataDetective produced data_profile for {len(file_paths)} file(s).")
        ],
    }
