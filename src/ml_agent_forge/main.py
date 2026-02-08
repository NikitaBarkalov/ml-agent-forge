"""CLI entry point: run the multi-agent graph with configurable or dummy input."""

import os
import argparse
from pathlib import Path

from dotenv import load_dotenv

from src.ml_agent_forge.graph import get_graph
from src.ml_agent_forge.state import GraphState

load_dotenv()


def run(
    business_context: str,
    task: str,
    metaData: str,
    file_paths: list[str],
) -> dict:
    """Run the graph and return the final state (including final_report)."""
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
    config = {"configurable": {"thread_id": "main"}}
    final_state = graph.invoke(initial_state, config=config)
    return final_state


def main():
    from src.ml_agent_forge.utils.logger import configure_logging, get_logger

    configure_logging()
    log = get_logger()
    log.info("Pipeline started", status = 'started')

    parser = argparse.ArgumentParser(description="Run ML/BA multi-agent pipeline")
    parser.add_argument("--business", type=str, default="E-commerce conversion analysis")
    parser.add_argument("--task", type=str, default="Analyze conversion funnel and suggest improvements.")
    parser.add_argument("--metaData", type=str, default="This dataset contains conversion performance metrics for different user or marketing segments.")
    parser.add_argument("--files", type=str, nargs="*", default=[], help="Paths to data files (CSV/Excel)")
    args = parser.parse_args()

    if not args.files:
        # Dummy: no real files; create a minimal CSV for demo if desired
        dummy_csv = Path("dummy_data.csv")
        if not dummy_csv.exists():
            dummy_csv.write_text("segment,visitors,conversions,rate\nA,1000,50,0.05\nB,800,120,0.15\nC,500,100,0.20\n")
            args.files = [str(dummy_csv)]
            print("Using dummy_data.csv (created). Set --files for your own data.")

    file_paths = [str(Path(p).resolve()) for p in args.files]
    for p in file_paths:
        if not Path(p).exists():
            print(f"Warning: file not found: {p}")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and set keys.")
        return 1
    if not os.getenv("E2B_API_KEY") and file_paths:
        print("Warning: E2B_API_KEY not set. Developer node (code execution) will fail.")

    log.info("Running pipeline", business=args.business, task=args.task[:100], metaData=args.metaData[:100], files=file_paths)
    state = run(args.business, args.task,args.metaData,file_paths)
    report = state.get("final_report") or ""
    log.info("Pipeline finished", status="pipeline_end", report_len=len(report))
    print("\n" + "=" * 60 + "\nFINAL REPORT\n" + "=" * 60 + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    exit(main())
