import csv
import importlib.util
from pathlib import Path


TOOL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "tools" / "render_rerender_manifest.py"


def _load_tool():
    assert TOOL_PATH.is_file(), "render manifest tool should exist"
    spec = importlib.util.spec_from_file_location("render_rerender_manifest", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_chunk_rows_uses_ceil_sized_contiguous_chunks():
    tool = _load_tool()
    rows = [{"uid": str(index)} for index in range(10)]

    assert [row["uid"] for row in tool.chunk_rows(rows, chunk_id=0, chunk_total=3)] == ["0", "1", "2", "3"]
    assert [row["uid"] for row in tool.chunk_rows(rows, chunk_id=1, chunk_total=3)] == ["4", "5", "6", "7"]
    assert [row["uid"] for row in tool.chunk_rows(rows, chunk_id=2, chunk_total=3)] == ["8", "9"]


def test_chunk_rows_rejects_invalid_chunk_arguments():
    tool = _load_tool()
    rows = [{"uid": "a"}]

    for chunk_id, chunk_total in [(-1, 3), (3, 3), (0, 0)]:
        try:
            tool.chunk_rows(rows, chunk_id=chunk_id, chunk_total=chunk_total)
        except ValueError as exc:
            assert "chunk" in str(exc)
        else:
            raise AssertionError("invalid chunk arguments should fail")


def test_build_render_inputs_preserves_category_uid_output_structure(tmp_path):
    tool = _load_tool()
    usd_path = tmp_path / "asset.usd"
    usd_path.write_text("#usda 1.0\n")
    rows = [
        {
            "category": "basket",
            "uid": "abc123",
            "usd_path": str(usd_path),
        }
    ]

    usd_paths, output_dirs = tool.build_render_inputs(rows, tmp_path / "renders")

    assert usd_paths == [usd_path]
    assert output_dirs == [tmp_path / "renders" / "basket" / "abc123"]


def test_build_render_inputs_rejects_category_or_uid_path_escape(tmp_path):
    tool = _load_tool()
    usd_path = tmp_path / "asset.usd"
    usd_path.write_text("#usda 1.0\n")

    bad_rows = [
        {"category": "..", "uid": "asset", "usd_path": str(usd_path)},
        {"category": ".", "uid": "asset", "usd_path": str(usd_path)},
        {"category": "basket", "uid": "../asset", "usd_path": str(usd_path)},
        {"category": "basket", "uid": "..", "usd_path": str(usd_path)},
        {"category": "basket", "uid": ".", "usd_path": str(usd_path)},
        {"category": "/tmp", "uid": "asset", "usd_path": str(usd_path)},
    ]
    for row in bad_rows:
        try:
            tool.build_render_inputs([row], tmp_path / "renders")
        except ValueError as exc:
            assert "unsafe" in str(exc)
        else:
            raise AssertionError("unsafe category/uid should fail")


def test_build_render_inputs_skips_missing_usds_when_requested(tmp_path):
    tool = _load_tool()
    existing = tmp_path / "asset.usd"
    existing.write_text("#usda 1.0\n")
    rows = [
        {"category": "basket", "uid": "exists", "usd_path": str(existing)},
        {"category": "basket", "uid": "missing", "usd_path": str(tmp_path / "missing.usd")},
    ]

    usd_paths, output_dirs, skipped = tool.build_render_inputs(
        rows,
        tmp_path / "renders",
        skip_missing=True,
    )

    assert usd_paths == [existing]
    assert output_dirs == [tmp_path / "renders" / "basket" / "exists"]
    assert skipped == [rows[1]]


def test_build_render_inputs_rejects_output_root_inside_source_dataset(tmp_path):
    tool = _load_tool()
    dataset_root = tmp_path / "GRScenes_assets"
    asset_dir = dataset_root / "basket" / "abc123"
    usd_path = asset_dir / "usd" / "abc123.usd"
    usd_path.parent.mkdir(parents=True)
    usd_path.write_text("#usda 1.0\n")
    rows = [
        {
            "category": "basket",
            "uid": "abc123",
            "asset_dir": str(asset_dir),
            "usd_path": str(usd_path),
        }
    ]

    try:
        tool.build_render_inputs(rows, dataset_root)
    except ValueError as exc:
        assert "source dataset" in str(exc)
    else:
        raise AssertionError("output root inside source dataset should fail")


def test_build_render_inputs_reports_missing_required_manifest_fields(tmp_path):
    tool = _load_tool()
    usd_path = tmp_path / "asset.usd"
    usd_path.write_text("#usda 1.0\n")
    rows = [{"category": "basket", "usd_path": str(usd_path)}]

    try:
        tool.build_render_inputs(rows, tmp_path / "renders")
    except ValueError as exc:
        assert "missing required manifest fields" in str(exc)
        assert "uid" in str(exc)
    else:
        raise AssertionError("missing manifest fields should fail clearly")


def test_read_manifest_filters_to_rerender_recommended_rows(tmp_path):
    tool = _load_tool()
    manifest = tmp_path / "manifest.csv"
    rows = [
        {"category": "basket", "uid": "a", "usd_path": "/tmp/a.usd", "rerender_recommended": "true"},
        {"category": "basket", "uid": "b", "usd_path": "/tmp/b.usd", "rerender_recommended": "false"},
    ]
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    filtered = tool.read_manifest_rows(manifest, recommended_only=True)
    unfiltered = tool.read_manifest_rows(manifest, recommended_only=False)

    assert [row["uid"] for row in filtered] == ["a"]
    assert [row["uid"] for row in unfiltered] == ["a", "b"]


def test_read_manifest_rejects_missing_rerender_recommended_column(tmp_path):
    tool = _load_tool()
    manifest = tmp_path / "manifest.csv"
    rows = [
        {"category": "basket", "uid": "a", "usd_path": "/tmp/a.usd"},
    ]
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    try:
        tool.read_manifest_rows(manifest, recommended_only=True)
    except ValueError as exc:
        assert "missing required manifest columns" in str(exc)
        assert "rerender_recommended" in str(exc)
    else:
        raise AssertionError("missing rerender_recommended should fail clearly")
