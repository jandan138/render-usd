import os
import subprocess

def submit_jobs(
    bash_command: str, 
) -> None:
    try:
        result = subprocess.run(bash_command, shell=True, capture_output=True, text=True, check=True)
        print(f"[SUCCESS] Job submitted successfully")
        if result.stdout:
            print(f"[STDOUT] {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed with exit code {e.returncode}")
        if e.stdout:
            print(f"[STDOUT] {e.stdout}")
        if e.stderr:
            print(f"[STDERR] {e.stderr}")
        raise e


def main():
    chunk_number = 30
    submitted_ids = [0, 1]
    for chunk_id in range(chunk_number):
        if chunk_id not in submitted_ids:
            bash_command = f"bash launch_render_grscenes100.sh {chunk_id} {chunk_number}"
            submit_jobs(bash_command)

if __name__ == "__main__":
    main()