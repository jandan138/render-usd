#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


CONFIG = {"headless": True, "anti_aliasing": 4, "multi_gpu": False, "renderer": "PathTracing"}
REQUIRED_FIELDS = ("category", "uid", "usd_path")
RECOMMENDATION_FIELD = "rerender_recommended"


def read_manifest_rows(manifest_csv: Path, recommended_only: bool = True) -> list[dict[str, str]]:
    with Path(manifest_csv).open(newline="") as handle:
        reader = csv.DictReader(handle)
        expected_fields = set(REQUIRED_FIELDS)
        if recommended_only:
            expected_fields.add(RECOMMENDATION_FIELD)
        missing_fields = sorted(expected_fields - set(reader.fieldnames or []))
        if missing_fields:
            raise ValueError(f"missing required manifest columns: {', '.join(missing_fields)}")
        rows = list(reader)
    if recommended_only:
        rows = [row for row in rows if row[RECOMMENDATION_FIELD] == "true"]
    return rows


def chunk_rows(rows: list[dict[str, str]], *, chunk_id: int, chunk_total: int) -> list[dict[str, str]]:
    if chunk_total <= 0 or chunk_id < 0 or chunk_id >= chunk_total:
        raise ValueError("chunk_id must be in [0, chunk_total) and chunk_total must be positive")
    chunk_size = (len(rows) + chunk_total - 1) // chunk_total
    start_idx = chunk_id * chunk_size
    end_idx = min(start_idx + chunk_size, len(rows))
    return rows[start_idx:end_idx]


def _safe_output_dir(output_root: Path, category: str, uid: str) -> Path:
    for name, value in (("category", category), ("uid", uid)):
        value_path = Path(value)
        if not value or value in {".", ".."} or value_path.is_absolute() or value_path.parts != (value,):
            raise ValueError(f"unsafe {name}: {value}")

    root = Path(output_root).resolve()
    output_dir = (root / category / uid).resolve()
    try:
        output_dir.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"unsafe output path: {output_dir}") from exc
    return output_dir


def _require_manifest_fields(row: dict[str, str]) -> None:
    missing = [field for field in REQUIRED_FIELDS if not row.get(field)]
    if missing:
        raise ValueError(f"missing required manifest fields: {', '.join(missing)}")


def _source_dataset_root(row: dict[str, str], usd_path: Path) -> Path | None:
    asset_dir = Path(row.get("asset_dir") or usd_path.parent.parent).resolve()
    if asset_dir.name == row["uid"] and asset_dir.parent.name == row["category"]:
        return asset_dir.parent.parent
    return None


def _ensure_output_root_outside_source_dataset(output_root: Path, row: dict[str, str], usd_path: Path) -> None:
    source_root = _source_dataset_root(row, usd_path)
    if source_root is None:
        return

    root = Path(output_root).resolve()
    if root == source_root or root.is_relative_to(source_root):
        raise ValueError(f"output root must be outside source dataset: {root}")


def build_render_inputs(
    rows: list[dict[str, str]],
    output_root: Path,
    *,
    skip_missing: bool = False,
):
    object_usd_paths = []
    output_dirs = []
    skipped_rows = []
    for row in rows:
        _require_manifest_fields(row)
        usd_path = Path(row["usd_path"])
        if not usd_path.is_file():
            if skip_missing:
                skipped_rows.append(row)
                continue
            raise FileNotFoundError(usd_path)
        _ensure_output_root_outside_source_dataset(output_root, row, usd_path)
        object_usd_paths.append(usd_path)
        output_dirs.append(_safe_output_dir(output_root, row["category"], row["uid"]))
    if skip_missing:
        return object_usd_paths, output_dirs, skipped_rows
    return object_usd_paths, output_dirs


def render_rows(
    rows: list[dict[str, str]],
    *,
    output_root: Path,
    naming_style: str = "view",
    overwrite: bool = False,
    skip_missing: bool = True,
) -> None:
    if skip_missing:
        object_usd_paths, output_dirs, skipped_rows = build_render_inputs(rows, output_root, skip_missing=True)
        for row in skipped_rows:
            print(f"[Warning] Missing USD, skipping: {row.get('category', '')}/{row.get('uid', '')} {row.get('usd_path', '')}")
    else:
        object_usd_paths, output_dirs = build_render_inputs(rows, output_root)
    if not object_usd_paths:
        print("No rows selected for this chunk; exiting.")
        return

    from isaacsim import SimulationApp

    kit = SimulationApp(CONFIG)
    try:
        from render_usd.cli import _collect_mdl_paths, _configure_mdl_search_paths
        from render_usd.core.renderer import RenderManager

        _configure_mdl_search_paths(_collect_mdl_paths(None))
        renderer = RenderManager(kit)
        try:
            renderer.render_thumbnail_wo_bg(
                object_usd_paths,
                output_dirs,
                show_bbox2d=False,
                sample_number=4,
                init_azimuth_angle=0,
                naming_style=naming_style,
                overwrite=overwrite,
            )
        finally:
            renderer.cleanup()
    finally:
        kit.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render USD rows from a rerender manifest.")
    parser.add_argument("--manifest_csv", type=Path, required=True)
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument("--chunk_id", type=int, default=0)
    parser.add_argument("--chunk_total", type=int, default=1)
    parser.add_argument("--naming_style", choices=("index", "view"), default="view")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--include_not_recommended", action="store_true")
    parser.add_argument("--fail_on_missing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_manifest_rows(
        args.manifest_csv,
        recommended_only=not args.include_not_recommended,
    )
    selected_rows = chunk_rows(rows, chunk_id=args.chunk_id, chunk_total=args.chunk_total)
    print(
        f"Rendering manifest chunk {args.chunk_id}/{args.chunk_total}: "
        f"{len(selected_rows)} rows from {len(rows)} manifest rows"
    )
    render_rows(
        selected_rows,
        output_root=args.output_root,
        naming_style=args.naming_style,
        overwrite=args.overwrite,
        skip_missing=not args.fail_on_missing,
    )


if __name__ == "__main__":
    main()
