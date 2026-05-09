from pathlib import Path
import subprocess


def test_run_task_exposes_render_manifest_mode():
    script = Path(__file__).resolve().parents[1] / "scripts" / "dlc" / "run_task.sh"
    text = script.read_text()

    assert 'elif [ "$1" == "render_manifest" ]' in text
    assert "scripts/tools/render_rerender_manifest.py" in text
    assert "--manifest_csv" in text
    assert "--output_root" in text
    assert "--chunk_id" in text
    assert "--chunk_total" in text


def test_run_task_manifest_mode_validates_required_args_and_explicit_overwrite():
    script = Path(__file__).resolve().parents[1] / "scripts" / "dlc" / "run_task.sh"
    text = script.read_text()

    assert "Usage: bash run_task.sh render_manifest <manifest_csv> <output_root>" in text
    assert 'if [ $# -lt 3 ]; then' in text
    assert 'if [ "$OVERWRITE" == "true" ]' in text
    assert 'elif [ -n "$OVERWRITE" ] && [ "$OVERWRITE" != "false" ]; then' in text


def test_run_task_shell_syntax_is_valid():
    script = Path(__file__).resolve().parents[1] / "scripts" / "dlc" / "run_task.sh"

    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_run_task_manifest_mode_preflights_output_root():
    script = Path(__file__).resolve().parents[1] / "scripts" / "dlc" / "run_task.sh"
    text = script.read_text()

    assert "OUTPUT_PARENT" in text
    assert '[ -e "$OUTPUT_ROOT" ] && [ ! -d "$OUTPUT_ROOT" ]' in text
    assert '[ ! -d "$OUTPUT_PARENT" ]' in text
