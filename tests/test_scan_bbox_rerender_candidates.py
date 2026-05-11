import csv
import importlib.util
from pathlib import Path

import numpy as np


TOOL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "tools" / "scan_bbox_rerender_candidates.py"


def _load_tool():
    assert TOOL_PATH.is_file(), "manifest scan tool should exist"
    spec = importlib.util.spec_from_file_location("scan_bbox_rerender_candidates", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_category_grouping_and_class_parsing():
    tool = _load_tool()

    assert tool.parse_classes(" blank, tiny , suspicious ") == {"blank", "tiny", "suspicious"}
    assert tool.category_group_for("wall") == "structural"
    assert tool.category_group_for("ground") == "structural"
    assert tool.category_group_for("ceiling") == "structural"
    assert tool.category_group_for("column") == "edge_thin"
    assert tool.category_group_for("window") == "edge_thin"
    assert tool.category_group_for("threshold") == "edge_thin"
    assert tool.category_group_for("other") == "other"
    assert tool.category_group_for("basket") == "object"


def test_recommendation_requires_changed_object_row_above_threshold():
    tool = _load_tool()

    assert tool.is_rerender_recommended(
        fallback_changed=True,
        diag_ratio=5.0,
        category_group="object",
        threshold=5.0,
    )
    assert not tool.is_rerender_recommended(
        fallback_changed=True,
        diag_ratio=4.999,
        category_group="object",
        threshold=5.0,
    )
    assert not tool.is_rerender_recommended(
        fallback_changed=True,
        diag_ratio=50.0,
        category_group="structural",
        threshold=5.0,
    )
    assert not tool.is_rerender_recommended(
        fallback_changed=False,
        diag_ratio=50.0,
        category_group="object",
        threshold=5.0,
    )


def test_recommendation_accepts_large_center_offset_with_same_diag():
    tool = _load_tool()

    assert tool.is_rerender_recommended(
        fallback_changed=True,
        diag_ratio=1.0,
        center_offset_ratio=2.0,
        category_group="object",
        threshold=5.0,
        center_offset_threshold=1.0,
    )


def test_recommendation_can_include_configured_category_groups():
    tool = _load_tool()

    assert tool.parse_category_groups(" object, edge_thin ") == {"object", "edge_thin"}
    assert tool.is_rerender_recommended(
        fallback_changed=True,
        diag_ratio=5.0,
        category_group="edge_thin",
        threshold=5.0,
        recommended_groups={"object", "edge_thin"},
    )


def test_scan_asset_rows_filters_classes_and_recommends_only_object_ratio_matches():
    tool = _load_tool()
    asset_rows = [
        {"category": "basket", "uid": "asset-a", "class": "tiny", "usd_path": "/tmp/a.usd"},
        {"category": "wall", "uid": "asset-b", "class": "blank", "usd_path": "/tmp/b.usd"},
        {"category": "chair", "uid": "asset-c", "class": "suspicious", "usd_path": "/tmp/c.usd"},
        {"category": "chair", "uid": "asset-d", "class": "ok", "usd_path": "/tmp/d.usd"},
    ]
    effects = {
        "/tmp/a.usd": {"old_diag": 100.0, "new_diag": 10.0, "diag_ratio": 10.0, "fallback_changed": True},
        "/tmp/b.usd": {"old_diag": 100.0, "new_diag": 10.0, "diag_ratio": 10.0, "fallback_changed": True},
        "/tmp/c.usd": {"old_diag": 12.0, "new_diag": 12.0, "diag_ratio": 1.0, "center_offset_ratio": 2.0, "fallback_changed": True},
    }

    def fake_scanner(path):
        return effects[str(path)]

    rows = tool.scan_asset_rows(
        asset_rows,
        class_filter={"blank", "tiny", "suspicious"},
        diag_ratio_threshold=5.0,
        bbox_scanner=fake_scanner,
    )

    assert [row["uid"] for row in rows] == ["asset-a", "asset-b", "asset-c"]
    assert rows[0]["image_class"] == "tiny"
    assert rows[0]["category_group"] == "object"
    assert rows[0]["old_diag"] == "100.000000"
    assert rows[0]["new_diag"] == "10.000000"
    assert rows[0]["diag_ratio"] == "10.000000"
    assert rows[0]["fallback_changed"] == "true"
    assert rows[0]["rerender_recommended"] == "true"
    assert rows[0]["scan_error"] == ""
    assert rows[1]["category_group"] == "structural"
    assert rows[1]["rerender_recommended"] == "false"
    assert rows[2]["fallback_changed"] == "true"
    assert rows[2]["center_offset_ratio"] == "2.000000"
    assert rows[2]["rerender_recommended"] == "true"


def test_scan_asset_rows_honors_non_default_center_offset_threshold():
    tool = _load_tool()
    asset_rows = [
        {"category": "bottle", "uid": "shifted", "class": "blank", "usd_path": "/tmp/shifted.usd"},
    ]

    def fake_scanner(path):
        return {
            "old_diag": 12.0,
            "new_diag": 12.0,
            "diag_ratio": 1.0,
            "center_offset_ratio": 2.0,
            "fallback_changed": True,
        }

    rows = tool.scan_asset_rows(
        asset_rows,
        class_filter={"blank"},
        diag_ratio_threshold=5.0,
        center_offset_threshold=3.0,
        bbox_scanner=fake_scanner,
    )

    assert rows[0]["fallback_changed"] == "true"
    assert rows[0]["center_offset_ratio"] == "2.000000"
    assert rows[0]["rerender_recommended"] == "false"


def test_scan_asset_rows_rejects_invalid_center_offset_threshold():
    tool = _load_tool()

    for center_offset_threshold in [0, -1, 0.5, float("inf"), float("nan")]:
        try:
            tool.scan_asset_rows(
                [{"category": "bottle", "uid": "shifted", "class": "blank", "usd_path": "/tmp/shifted.usd"}],
                class_filter={"blank"},
                diag_ratio_threshold=5.0,
                center_offset_threshold=center_offset_threshold,
                bbox_scanner=lambda path: {},
            )
        except ValueError as exc:
            assert "center_offset_threshold" in str(exc)
        else:
            raise AssertionError("invalid center offset threshold should fail")


def test_scan_asset_rows_preserves_error_rows_as_not_recommended():
    tool = _load_tool()
    asset_rows = [
        {"category": "cabinet", "uid": "bad-usd", "class": "tiny", "usd_path": "/tmp/missing.usd"},
    ]

    def failing_scanner(path):
        raise RuntimeError(f"cannot open {path}")

    rows = tool.scan_asset_rows(
        asset_rows,
        class_filter={"tiny"},
        diag_ratio_threshold=5.0,
        bbox_scanner=failing_scanner,
    )

    assert len(rows) == 1
    assert rows[0]["category_group"] == "object"
    assert rows[0]["old_diag"] == ""
    assert rows[0]["new_diag"] == ""
    assert rows[0]["diag_ratio"] == ""
    assert rows[0]["fallback_changed"] == "false"
    assert rows[0]["rerender_recommended"] == "false"
    assert "cannot open /tmp/missing.usd" in rows[0]["scan_error"]


def test_scan_asset_rows_marks_zero_or_nonfinite_fallback_as_unchanged():
    tool = _load_tool()
    asset_rows = [
        {"category": "cabinet", "uid": "zero", "class": "tiny", "usd_path": "/tmp/zero.usd"},
        {"category": "cabinet", "uid": "nan", "class": "tiny", "usd_path": "/tmp/nan.usd"},
    ]
    effects = {
        "/tmp/zero.usd": {"old_diag": 100.0, "new_diag": 0.0, "diag_ratio": float("inf"), "fallback_changed": True},
        "/tmp/nan.usd": {"old_diag": 100.0, "new_diag": float("nan"), "diag_ratio": float("nan"), "fallback_changed": True},
    }

    def fake_scanner(path):
        return effects[str(path)]

    rows = tool.scan_asset_rows(
        asset_rows,
        class_filter={"tiny"},
        diag_ratio_threshold=5.0,
        bbox_scanner=fake_scanner,
    )

    assert [row["fallback_changed"] for row in rows] == ["false", "false"]
    assert [row["rerender_recommended"] for row in rows] == ["false", "false"]


def test_bbox_effect_omits_ratio_when_fallback_bbox_is_invalid():
    tool = _load_tool()
    old_bbox = np.array([[0, 0, 0], [10, 0, 0]], dtype=float)
    zero_bbox = np.array([[1, 1, 1], [1, 1, 1]], dtype=float)
    nan_bbox = np.array([[0, 0, 0], [float("nan"), 1, 1]], dtype=float)

    zero_effect = tool.bbox_effect_from_bboxes(old_bbox, zero_bbox)
    nan_effect = tool.bbox_effect_from_bboxes(old_bbox, nan_bbox)

    assert zero_effect["fallback_changed"] is False
    assert zero_effect["diag_ratio"] == ""
    assert nan_effect["fallback_changed"] is False
    assert nan_effect["diag_ratio"] == ""


def test_write_outputs_creates_full_recommended_and_summary_files(tmp_path):
    tool = _load_tool()
    rows = [
        {
            "category": "basket",
            "uid": "asset-a",
            "image_class": "tiny",
            "category_group": "object",
            "old_diag": "100.000000",
            "new_diag": "10.000000",
            "diag_ratio": "10.000000",
            "fallback_changed": "true",
            "rerender_recommended": "true",
            "scan_error": "",
            "usd_path": "/tmp/a.usd",
        },
        {
            "category": "wall",
            "uid": "asset-b",
            "image_class": "blank",
            "category_group": "structural",
            "old_diag": "100.000000",
            "new_diag": "10.000000",
            "diag_ratio": "10.000000",
            "fallback_changed": "true",
            "rerender_recommended": "false",
            "scan_error": "",
            "usd_path": "/tmp/b.usd",
        },
    ]

    tool.write_outputs(
        rows,
        tmp_path,
        source_csv=Path("asset_quality.csv"),
        class_filter={"blank", "tiny", "suspicious"},
        diag_ratio_threshold=5.0,
    )

    manifest_rows = list(csv.DictReader((tmp_path / "bbox_rerender_manifest.csv").open()))
    recommended_rows = list(csv.DictReader((tmp_path / "bbox_rerender_recommended.csv").open()))
    summary = (tmp_path / "bbox_rerender_summary.md").read_text()

    assert [row["uid"] for row in manifest_rows] == ["asset-a", "asset-b"]
    assert [row["uid"] for row in recommended_rows] == ["asset-a"]
    assert "total_scanned: 2" in summary
    assert "recommended: 1" in summary
    assert "center_offset_threshold: 1.000000" in summary
    assert "tiny: 1" in summary
    assert "blank: 1" in summary
    assert "object: 1" in summary
    assert "structural: 1" in summary
    assert "true: 1" in summary
    assert "false: 1" in summary
