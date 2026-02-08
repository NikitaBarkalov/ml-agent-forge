"""DataDetective agent: analyzes input files and produces data_profile."""

import os
from pathlib import Path

from structlog import get_logger
from langchain_core.messages import HumanMessage

from src.ml_agent_forge.state import GraphState


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
    if suffix == ".json":
        return _profile_json(file_path)
    if suffix == ".parquet":
        return _profile_parquet(file_path)
    if suffix == ".pdf":
        return _profile_pdf(file_path)
    if suffix in (".txt", ".md"):
        return _profile_text(file_path)
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


def _profile_json(file_path: str) -> str:
    """Analyze a JSON file."""
    try:
        import pandas as pd
        df = pd.read_json(file_path)
        if df.empty:
            return f"JSON: {file_path} (empty)"
        head = df.head(5).to_string()
        dtypes = df.dtypes.to_string()
        return f"JSON: {file_path}\n--- head (5) ---\n{head}\n--- dtypes ---\n{dtypes}"
    except Exception as e:
        return f"JSON {file_path} error: {e!s}"


def _profile_parquet(file_path: str) -> str:
    """Analyze a Parquet file."""
    try:
        import pandas as pd
        df = pd.read_parquet(file_path)
        head = df.head(5).to_string()
        dtypes = df.dtypes.to_string()
        return f"Parquet: {file_path}\n--- head (5) ---\n{head}\n--- dtypes ---\n{dtypes}"
    except Exception as e:
        return f"Parquet {file_path} error: {e!s}"


def _profile_pdf(file_path: str) -> str:
    """Extract metadata and a text preview from a PDF."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        info = reader.metadata
        pages_count = len(reader.pages)
        
        # Extract preview text from the first few pages
        text_parts = []
        for i in range(min(3, pages_count)):
            text_parts.append(reader.pages[i].extract_text() or "")
        
        full_text = "\n".join(text_parts)
        preview = full_text[:1000] + "..." if len(full_text) > 1000 else full_text
        
        return f"PDF: {file_path}\n--- pages: {pages_count} ---\n--- metadata ---\n{info}\n--- preview (first ~1000 chars) ---\n{preview}"
    except Exception as e:
        return f"PDF {file_path} error: {e!s}"


def _profile_text(file_path: str) -> str:
    """Analyze a plain text or markdown file."""
    try:
        text = Path(file_path).read_text(encoding="utf-8")
        lines = text.splitlines()
        preview = "\n".join(lines[:10])
        return f"Text: {file_path}\n--- line count: {len(lines)} ---\n--- preview (10 lines) ---\n{preview}"
    except Exception as e:
        return f"Text {file_path} error: {e!s}"


def detective_node(state: GraphState) -> dict:
    """Analyze files from user_input['file_paths'] and set data_profile."""
    user_input = state.get("user_input") or {}
    file_paths = user_input.get("file_paths") or []
    task = user_input.get("task", "")
    get_logger().info(
        "Agent started",
        agent="DataDetective",
        task=task[:200] + "..." if len(task) > 200 else task,
        file_paths=file_paths,
    )
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
