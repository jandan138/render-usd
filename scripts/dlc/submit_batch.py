import argparse
import subprocess
import sys
from pathlib import Path


def submit_jobs(
    chunk_total: int,
    task_name: str,
    data_sources: str | None = None,
    command_args: str | None = None,
) -> None:
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
        # 参数4: data_sources (传空字符串让 launch_job.sh 使用默认值)
        cmd.append(data_sources if data_sources else "")
        # 参数5: command_args (可选, 覆盖 run_task.sh 的运行模式)
        # 支持 {chunk_id} 和 {chunk_total} 模板替换
        if command_args:
            # 替换模板变量为实际的 chunk_id 和 chunk_total
            expanded_args = command_args.replace("{chunk_id}", str(chunk_id)).replace("{chunk_total}", str(chunk_total))
            cmd.append(expanded_args)
        print(f"Executing: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, cwd=str(repo_root))


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit batch DLC rendering jobs")
    parser.add_argument("--total", type=int, required=True, help="Total chunk count")
    parser.add_argument("--name", type=str, default="render_grscenes100", help="Base task name")
    parser.add_argument("--data_sources", type=str, default=None, help="Comma-separated data source IDs")
    parser.add_argument("--command_args", type=str, default=None,
                        help="Custom run_task.sh args (e.g. 'render_custom /path/to/assets')")
    args = parser.parse_args()

    if args.total <= 0:
        print("ERROR: --total must be a positive integer", file=sys.stderr)
        raise SystemExit(2)

    submit_jobs(args.total, args.name, args.data_sources, args.command_args)


if __name__ == "__main__":
    main()
