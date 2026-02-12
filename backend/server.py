"""FastAPI web server: upload, WebSocket-run with live logs, download."""

import asyncio
import os
import uuid
from pathlib import Path
from queue import Empty, Queue

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.graph import get_graph
from backend.state import GraphState
from backend.utils.logger import configure_logging, get_logger, set_log_queue

load_dotenv()

# Ensure uploads and outputs directories exist
UPLOADS_DIR = Path("uploads")
OUTPUTS_DIR = Path("outputs")
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

configure_logging()
log = get_logger()

app = FastAPI(title="ML Agent Forge", description="Multi-agent ML & BA pipeline")


def _run_graph(business_context: str, task: str, metaData: str, file_paths: list[str], log_queue: Queue) -> dict:
    """Run the graph synchronously. Sets log_queue in thread context for WebSocket streaming."""
    set_log_queue(log_queue)
    try:
        initial_state: GraphState = {
            "messages": [],
            "user_input": {
                "business_context": business_context,
                "task": task,
                "metaData": metaData,
                "file_paths": file_paths,
            },
            "data_profile": "",
            "plan": "",
            "code_context": [],
            "final_report": "",
            "next_agent": "",
        }
        graph = get_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = graph.invoke(initial_state, config=config)
        return dict(final_state)
    finally:
        set_log_queue(None)


def _save_outputs(session_id: str, state: dict) -> dict[str, str]:
    """Save report, pipeline code, and artifacts to outputs/{session_id}/. Returns file paths."""
    out_dir = OUTPUTS_DIR / session_id
    out_dir.mkdir(exist_ok=True)
    paths = {}

    # Save final report
    report = state.get("final_report") or ""
    report_path = out_dir / "final_report.md"
    report_path.write_text(report, encoding="utf-8")
    paths["report"] = f"{session_id}/final_report.md"

    # Save pipeline code from code_context
    code_context = state.get("code_context") or []
    code_parts = []
    import base64
    for i, ctx in enumerate(code_context):
        c = ctx.get("code")
        if c:
            code_parts.append(f"# --- Run {i + 1} ---\n{c}\n")
        
        # Save artifacts (e.g. plots)
        artifacts = ctx.get("artifacts") or []
        for j, art in enumerate(artifacts):
            art_path_raw = art.get("path", "")
            content_b64 = art.get("content_base64", "")
            if content_b64:
                # Use the filename from the sandbox path or a generated one
                name = Path(art_path_raw).name if art_path_raw else f"artifact_{i}_{j}.png"
                (out_dir / name).write_bytes(base64.b64decode(content_b64))

    if code_parts:
        pipeline_path = out_dir / "pipeline.py"
        pipeline_path.write_text("\n".join(code_parts), encoding="utf-8")
        paths["pipeline"] = f"{session_id}/pipeline.py"

    return paths


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """Accept uploaded CSV or Excel file and save to uploads/."""
    suffix = Path(file.filename or "").suffix.lower()
    allowed = (".csv", ".xlsx", ".xls", ".json", ".parquet", ".pdf", ".txt", ".png", ".jpg", ".jpeg", ".zip")
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"File type {suffix} not supported")

    file_id = f"{uuid.uuid4().hex[:12]}{suffix}"
    path = UPLOADS_DIR / file_id
    content = await file.read()
    path.write_bytes(content)
    return {"filename": file_id, "path": str(path.resolve())}


@app.websocket("/ws/run")
async def ws_run(websocket: WebSocket):
    """WebSocket: receive business_context, task, file_paths; run graph; stream logs and result."""
    await websocket.accept()
    session_id = uuid.uuid4().hex[:12]
    log_queue: Queue = Queue()

    try:
        # Receive initial payload
        data = await websocket.receive_json()
        business_context = data.get("business_context", "")
        task = data.get("task", "")
        metaData = data.get("metaData", "")
        file_paths_raw = data.get("file_paths", [])

        # Resolve file paths (filenames from /upload are stored in uploads/)
        file_paths = []
        for fp in file_paths_raw:
            if isinstance(fp, str):
                p = UPLOADS_DIR / fp if not Path(fp).is_absolute() else Path(fp)
                if p.exists():
                    file_paths.append(str(p.resolve()))

        def resolve_field_file(fname):
            if not fname: return None
            p = UPLOADS_DIR / fname if not Path(fname).is_absolute() else Path(fname)
            return str(p.resolve()) if p.exists() else None

        initial_state: GraphState = {
            "messages": [],
            "user_input": {
                "business_context": business_context,
                "task": task,
                "metaData": metaData,
                "file_paths": file_paths,
                "context_file": resolve_field_file(data.get("context_file")),
                "task_file": resolve_field_file(data.get("task_file")),
                "metadata_file": resolve_field_file(data.get("metadata_file")),
            },
            "data_profile": "",
            "plan": "",
            "code_context": [],
            "final_report": "",
            "next_agent": "",
        }

        if not file_paths:
            # Allow running without files (dummy data)
            dummy = UPLOADS_DIR / "dummy_data.csv"
            if not dummy.exists():
                dummy.write_text(
                    "segment,visitors,conversions,rate\nA,1000,50,0.05\nB,800,120,0.15\nC,500,100,0.20\n"
                )
            file_paths = [str(dummy.resolve())]
            initial_state["user_input"]["file_paths"] = file_paths

        loop = asyncio.get_running_loop()
        
        # Wrapper to pass the initial_state to the graph
        def run_with_state():
            set_log_queue(log_queue)
            try:
                graph = get_graph()
                # Fresh thread_id for every run
                config = {"configurable": {"thread_id": str(uuid.uuid4())}}
                final_state = graph.invoke(initial_state, config=config)
                return dict(final_state)
            finally:
                # Push None sentinel to indicate end of logging
                log_queue.put(None)
                set_log_queue(None)

        future = loop.run_in_executor(None, run_with_state)

        # Drain log queue and send to WebSocket while graph runs
        async def drain_logs():
            while True:
                try:
                    ev = log_queue.get_nowait()
                    if ev is None:
                        break # Sentinel reached
                    await websocket.send_json(ev)
                except Empty:
                    if future.done() and log_queue.empty():
                        break
                    await asyncio.sleep(0.02)

        # Wait for both worker and log drainer
        state, _ = await asyncio.gather(future, drain_logs())

        # Drain any final logs
        while True:
            try:
                ev = log_queue.get_nowait()
                await websocket.send_json(ev)
            except Empty:
                break

        # Save outputs and send done
        saved = _save_outputs(session_id, state)
        await websocket.send_json({
            "type": "done",
            "session_id": session_id,
            "report_len": len(state.get("final_report") or ""),
            "downloads": saved,
        })

    except WebSocketDisconnect:
        log.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        log.exception("WebSocket run failed")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass


@app.get("/download/{path:path}")
async def download_file(path: str):
    """Download generated report, pipeline, or artifact. Path format: {session_id}/filename."""
    full_path = OUTPUTS_DIR / path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    # Security: ensure path is within OUTPUTS_DIR
    try:
        full_path.resolve().relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid path")
    return FileResponse(full_path, filename=full_path.name)


# Static files path (project root / static)
_project_root = Path(__file__).resolve().parent.parent #.parent
static_dir = _project_root / "frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main UI."""
    print(static_dir)
    index_path = static_dir / "index.html"
    print(index_path)
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "ML Agent Forge API. Serve static/index.html for the UI."}


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
