import argparse
import subprocess
import sys
from pathlib import Path


def submit_jobs(chunk_total: int, task_name: str, data_sources: str | None = None) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    launch_script = repo_root / "scripts" / "dlc" / "launch_job.sh"
    if not launch_script.exists():
        print(f"ERROR: launch script not found: {launch_script}", file=sys.stderr)
        raise SystemExit(1)

    for chunk_id in range(chunk_total):
        cmd: list[str] = [
            "bash",
            str(launch_script),
            task_name,
            str(chunk_id),
            str(chunk_total),
        ]
        if data_sources:
            cmd.append(data_sources)
        print(f"Executing: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, cwd=str(repo_root))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, required=True, help="Total chunk count")
    parser.add_argument("--name", type=str, default="render_grscenes100", help="Base task name")
    parser.add_argument("--data_sources", type=str, default=None, help="Comma-separated data source IDs")
    args = parser.parse_args()

    if args.total <= 0:
        print("ERROR: --total must be a positive integer", file=sys.stderr)
        raise SystemExit(2)

    submit_jobs(args.total, args.name, args.data_sources)


if __name__ == "__main__":
    main()
