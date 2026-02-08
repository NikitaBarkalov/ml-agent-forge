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

from src.ml_agent_forge.graph import get_graph
from src.ml_agent_forge.state import GraphState
from src.ml_agent_forge.utils.logger import configure_logging, get_logger, set_log_queue

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
    for i, ctx in enumerate(code_context):
        c = ctx.get("code")
        if c:
            code_parts.append(f"# --- Run {i + 1} ---\n{c}\n")
    if code_parts:
        pipeline_path = out_dir / "pipeline.py"
        pipeline_path.write_text("\n".join(code_parts), encoding="utf-8")
        paths["pipeline"] = f"{session_id}/pipeline.py"

    return paths


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """Accept uploaded CSV or Excel file and save to uploads/."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are allowed")

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

        if not file_paths:
            # Allow running without files (dummy data)
            dummy = UPLOADS_DIR / "dummy_data.csv"
            if not dummy.exists():
                dummy.write_text(
                    "segment,visitors,conversions,rate\nA,1000,50,0.05\nB,800,120,0.15\nC,500,100,0.20\n"
                )
            file_paths = [str(dummy.resolve())]

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            _run_graph,
            business_context,
            task,
            metaData,
            file_paths,
            log_queue,
        )

        # Drain log queue and send to WebSocket while graph runs
        async def drain_logs():
            while not future.done():
                try:
                    ev = log_queue.get_nowait()
                    await websocket.send_json(ev)
                except Empty:
                    await asyncio.sleep(0.05)
            # Drain remaining
            while True:
                try:
                    ev = log_queue.get_nowait()
                    await websocket.send_json(ev)
                except Empty:
                    break

        drain_task = asyncio.create_task(drain_logs())
        state = await future
        drain_task.cancel()
        try:
            await drain_task
        except asyncio.CancelledError:
            pass

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
_project_root = Path(__file__).resolve().parent.parent.parent
static_dir = _project_root / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main UI."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "ML Agent Forge API. Serve static/index.html for the UI."}


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
