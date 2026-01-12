import subprocess
import argparse
import os

def submit_jobs(chunk_total, task_name="render_grscenes100"):
    for chunk_id in range(chunk_total):
        cmd = f"bash scripts/dlc/launch_job.sh {task_name} {chunk_id} {chunk_total}"
        print(f"Executing: {cmd}")
        subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, default=30, help="Total number of chunks")
    parser.add_argument("--name", type=str, default="render_grscenes100", help="Base name for the task")
    args = parser.parse_args()
    
    # Ensure we are in the root
    if not os.path.exists("scripts/dlc/launch_job.sh"):
        print("Error: Please run this script from the project root.")
        exit(1)
        
    submit_jobs(args.total, args.name)
