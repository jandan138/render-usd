#!/usr/bin/env python3
import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np
from pxr import Usd

from render_usd.utils.usd_utils.prim_utils import compute_bbox


DEFAULT_CLASSES = "blank,tiny,suspicious"
DEFAULT_RECOMMENDED_GROUPS = "object"
STRUCTURAL_CATEGORIES = {"wall", "ground", "ceiling"}
EDGE_THIN_CATEGORIES = {"column", "window", "threshold"}
OTHER_CATEGORIES = {"other"}
VALID_CATEGORY_GROUPS = {"object", "structural", "edge_thin", "other"}

MANIFEST_FIELDNAMES = [
    "category",
    "uid",
    "image_class",
    "category_group",
    "old_diag",
    "new_diag",
    "diag_ratio",
    "fallback_changed",
    "rerender_recommended",
    "scan_error",
    "best_fg_ratio",
    "best_bbox_area_ratio",
    "best_max_dim",
    "view_classes",
    "asset_dir",
    "usd_path",
]


def parse_classes(classes_text: str) -> set[str]:
    classes = {value.strip() for value in classes_text.split(",") if value.strip()}
    if not classes:
        raise ValueError("at least one class must be provided")
    return classes


def parse_category_groups(groups_text: str) -> set[str]:
    groups = parse_classes(groups_text)
    invalid_groups = groups - VALID_CATEGORY_GROUPS
    if invalid_groups:
        raise ValueError(f"invalid category groups: {','.join(sorted(invalid_groups))}")
    return groups


def category_group_for(category: str) -> str:
    normalized = category.strip().lower()
    if normalized in STRUCTURAL_CATEGORIES:
        return "structural"
    if normalized in EDGE_THIN_CATEGORIES:
        return "edge_thin"
    if normalized in OTHER_CATEGORIES:
        return "other"
    return "object"


def diag(bbox) -> float:
    bbox = np.asarray(bbox, dtype=float)
    return float(np.linalg.norm(bbox[1] - bbox[0]))


def format_float(value) -> str:
    if value == "" or value is None:
        return ""
    value = float(value)
    if np.isposinf(value):
        return "inf"
    if np.isneginf(value):
        return "-inf"
    if np.isnan(value):
        return "nan"
    return f"{value:.6f}"


def format_bool(value: bool) -> str:
    return "true" if value else "false"


def is_rerender_recommended(
    *,
    fallback_changed: bool,
    diag_ratio: float,
    category_group: str,
    threshold: float,
    recommended_groups: set[str] | None = None,
) -> bool:
    recommended_groups = recommended_groups or {"object"}
    return bool(
        fallback_changed
        and category_group in recommended_groups
        and np.isfinite(diag_ratio)
        and diag_ratio >= threshold
    )


def _select_scan_prim(stage: Usd.Stage) -> Usd.Prim:
    default_prim = stage.GetDefaultPrim()
    if default_prim and default_prim.IsValid():
        return default_prim
    return stage.GetPseudoRoot()


def bbox_effect_from_bboxes(old_bbox, new_bbox) -> dict[str, object]:
    old_bbox = np.asarray(old_bbox, dtype=float)
    new_bbox = np.asarray(new_bbox, dtype=float)
    old_diag = diag(old_bbox)
    new_diag = diag(new_bbox)
    fallback_valid = bool(np.isfinite(new_bbox).all() and np.isfinite(new_diag) and new_diag > 0)
    fallback_changed = bool(fallback_valid and not np.allclose(old_bbox, new_bbox))
    diag_ratio = ""
    if fallback_valid and np.isfinite(old_diag):
        diag_ratio = old_diag / new_diag
    return {
        "old_diag": old_diag,
        "new_diag": new_diag,
        "diag_ratio": diag_ratio,
        "fallback_changed": fallback_changed,
        "scan_error": "",
    }


def scan_usd_bbox_effect(usd_path: Path) -> dict[str, object]:
    usd_path = Path(usd_path)
    stage = Usd.Stage.Open(str(usd_path))
    if stage is None:
        raise RuntimeError(f"open failed: {usd_path}")

    prim = _select_scan_prim(stage)
    old_bbox = compute_bbox(prim, use_mesh_point_fallback=False)
    new_bbox = compute_bbox(prim)
    return bbox_effect_from_bboxes(old_bbox, new_bbox)


def _empty_effect(scan_error: str) -> dict[str, object]:
    return {
        "old_diag": "",
        "new_diag": "",
        "diag_ratio": "",
        "fallback_changed": False,
        "scan_error": scan_error,
    }


def _manifest_row(
    asset_row: dict[str, str],
    effect: dict[str, object],
    threshold: float,
    recommended_groups: set[str],
) -> dict[str, str]:
    category = asset_row.get("category", "")
    category_group = category_group_for(category)
    image_class = asset_row.get("class") or asset_row.get("image_class", "")
    scan_error = str(effect.get("scan_error") or "")
    diag_ratio_value = effect.get("diag_ratio", "")
    numeric_diag_ratio = float(diag_ratio_value) if diag_ratio_value not in {"", None} else 0.0
    new_diag_value = effect.get("new_diag", "")
    numeric_new_diag = float(new_diag_value) if new_diag_value not in {"", None} else 0.0
    fallback_changed = bool(effect.get("fallback_changed")) and not scan_error
    fallback_changed = fallback_changed and np.isfinite(numeric_new_diag) and numeric_new_diag > 0
    recommended = False
    if not scan_error:
        recommended = is_rerender_recommended(
            fallback_changed=fallback_changed,
            diag_ratio=numeric_diag_ratio,
            category_group=category_group,
            threshold=threshold,
            recommended_groups=recommended_groups,
        )

    return {
        "category": category,
        "uid": asset_row.get("uid", ""),
        "image_class": image_class,
        "category_group": category_group,
        "old_diag": format_float(effect.get("old_diag", "")),
        "new_diag": format_float(effect.get("new_diag", "")),
        "diag_ratio": format_float(effect.get("diag_ratio", "")),
        "fallback_changed": format_bool(fallback_changed),
        "rerender_recommended": format_bool(recommended),
        "scan_error": scan_error,
        "best_fg_ratio": asset_row.get("best_fg_ratio", ""),
        "best_bbox_area_ratio": asset_row.get("best_bbox_area_ratio", ""),
        "best_max_dim": asset_row.get("best_max_dim", ""),
        "view_classes": asset_row.get("view_classes", ""),
        "asset_dir": asset_row.get("asset_dir", ""),
        "usd_path": asset_row.get("usd_path", ""),
    }


def scan_asset_rows(
    asset_rows,
    *,
    class_filter: set[str],
    diag_ratio_threshold: float,
    bbox_scanner=scan_usd_bbox_effect,
    recommended_groups: set[str] | None = None,
    limit: int | None = None,
    progress_every: int = 0,
) -> list[dict[str, str]]:
    if not np.isfinite(diag_ratio_threshold) or diag_ratio_threshold <= 0:
        raise ValueError("diag_ratio_threshold must be finite and positive")

    recommended_groups = recommended_groups or {"object"}
    manifest_rows = []
    for asset_row in asset_rows:
        image_class = asset_row.get("class") or asset_row.get("image_class", "")
        if image_class not in class_filter:
            continue
        if limit is not None and len(manifest_rows) >= limit:
            break

        try:
            effect = bbox_scanner(Path(asset_row.get("usd_path", "")))
        except Exception as exc:
            effect = _empty_effect(str(exc))
        manifest_rows.append(_manifest_row(asset_row, effect, diag_ratio_threshold, recommended_groups))

        if progress_every > 0 and len(manifest_rows) % progress_every == 0:
            print(f"scanned={len(manifest_rows)}")

    return manifest_rows


def read_asset_quality_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def build_summary_markdown(
    rows: list[dict[str, str]],
    *,
    source_csv: Path,
    class_filter: set[str],
    diag_ratio_threshold: float,
    recommended_groups: set[str] | None = None,
) -> str:
    recommended_groups = recommended_groups or {"object"}
    image_class_counts = Counter(row["image_class"] for row in rows)
    group_counts = Counter(row["category_group"] for row in rows)
    recommendation_counts = Counter(row["rerender_recommended"] for row in rows)
    recommended_count = sum(row["rerender_recommended"] == "true" for row in rows)
    fallback_changed_count = sum(row["fallback_changed"] == "true" for row in rows)
    error_count = sum(bool(row["scan_error"]) for row in rows)

    lines = [
        "# BBox-Ratio Rerender Manifest Summary",
        "",
        "## Inputs",
        "",
        f"source_csv: {source_csv}",
        f"classes: {','.join(sorted(class_filter))}",
        f"recommended_groups: {','.join(sorted(recommended_groups))}",
        f"diag_ratio_threshold: {diag_ratio_threshold:.6f}",
        "",
        "## Totals",
        "",
        f"total_scanned: {len(rows)}",
        f"recommended: {recommended_count}",
        f"fallback_changed: {fallback_changed_count}",
        f"scan_errors: {error_count}",
        "",
        "## Counts By Image Class",
        "",
    ]
    lines.extend(f"{key}: {value}" for key, value in sorted(image_class_counts.items()))
    lines.extend(["", "## Counts By Category Group", ""])
    lines.extend(f"{key}: {value}" for key, value in sorted(group_counts.items()))
    lines.extend(["", "## Counts By Recommendation", ""])
    lines.extend(f"{key}: {value}" for key, value in sorted(recommendation_counts.items()))
    return "\n".join(lines) + "\n"


def write_outputs(
    rows: list[dict[str, str]],
    output_dir: Path,
    *,
    source_csv: Path,
    class_filter: set[str],
    diag_ratio_threshold: float,
    recommended_groups: set[str] | None = None,
) -> None:
    recommended_groups = recommended_groups or {"object"}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "bbox_rerender_manifest.csv", rows)
    recommended_rows = [row for row in rows if row["rerender_recommended"] == "true"]
    write_csv(output_dir / "bbox_rerender_recommended.csv", recommended_rows)
    summary = build_summary_markdown(
        rows,
        source_csv=source_csv,
        class_filter=class_filter,
        diag_ratio_threshold=diag_ratio_threshold,
        recommended_groups=recommended_groups,
    )
    (output_dir / "bbox_rerender_summary.md").write_text(summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan image-quality rows for bbox-fallback rerender candidates.")
    parser.add_argument("--asset_quality_csv", required=True, type=Path)
    parser.add_argument("--output_dir", required=True, type=Path)
    parser.add_argument("--diag_ratio_threshold", type=float, default=5.0)
    parser.add_argument("--classes", default=DEFAULT_CLASSES)
    parser.add_argument("--recommended_groups", default=DEFAULT_RECOMMENDED_GROUPS)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--progress_every", type=int, default=500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    class_filter = parse_classes(args.classes)
    recommended_groups = parse_category_groups(args.recommended_groups)
    asset_rows = read_asset_quality_csv(args.asset_quality_csv)
    rows = scan_asset_rows(
        asset_rows,
        class_filter=class_filter,
        diag_ratio_threshold=args.diag_ratio_threshold,
        recommended_groups=recommended_groups,
        limit=args.limit,
        progress_every=args.progress_every,
    )
    write_outputs(
        rows,
        args.output_dir,
        source_csv=args.asset_quality_csv,
        class_filter=class_filter,
        diag_ratio_threshold=args.diag_ratio_threshold,
        recommended_groups=recommended_groups,
    )
    recommended_count = sum(row["rerender_recommended"] == "true" for row in rows)
    print(f"scanned={len(rows)} recommended={recommended_count}")
    print(f"wrote={args.output_dir / 'bbox_rerender_manifest.csv'}")
    print(f"wrote={args.output_dir / 'bbox_rerender_recommended.csv'}")
    print(f"wrote={args.output_dir / 'bbox_rerender_summary.md'}")


if __name__ == "__main__":
    main()
