import argparse
import csv
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


VIEW_NAMES = ("front", "left", "back", "right")
BG_RGB = np.asarray((40, 40, 40), dtype=np.float32)


def read_rgb(path):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        return None
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def compute_metrics(image, fg_threshold=10.0):
    rgb = image[:, :, :3].astype(np.float32)
    fg_mask = np.linalg.norm(rgb - BG_RGB, axis=2) > fg_threshold
    height, width = fg_mask.shape
    fg_ratio = float(fg_mask.sum()) / float(height * width)
    if not fg_mask.any():
        return fg_ratio, 0, 0, 0.0
    ys, xs = np.nonzero(fg_mask)
    bbox_width = int(xs.max() - xs.min() + 1)
    bbox_height = int(ys.max() - ys.min() + 1)
    bbox_area_ratio = (bbox_width * bbox_height) / float(height * width)
    return fg_ratio, bbox_width, bbox_height, bbox_area_ratio


def classify_view(fg_ratio, bbox_width, bbox_height, bbox_area_ratio):
    if fg_ratio <= 0.001:
        return "blank"
    if bbox_area_ratio <= 0.02 and max(bbox_width, bbox_height) <= 80:
        return "tiny"
    return "ok"


def classify_asset(view_classes, best_fg_ratio, best_bbox_area_ratio, best_max_dim):
    if len(view_classes) != len(VIEW_NAMES) or "missing" in view_classes:
        return "missing"
    if all(view_class == "blank" for view_class in view_classes) or best_fg_ratio <= 0.001:
        return "blank"
    if all(view_class in {"blank", "tiny"} for view_class in view_classes) or (
        best_bbox_area_ratio <= 0.02 and best_max_dim <= 80
    ):
        return "tiny"
    if any(view_class in {"blank", "tiny"} for view_class in view_classes):
        return "suspicious"
    return "ok"


def fmt(value):
    return f"{value:.6f}"


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze selected rerender output quality.")
    parser.add_argument("--selected_csv", type=Path, required=True)
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument("--analysis_dir", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    selected_rows = list(csv.DictReader(args.selected_csv.open(newline="")))
    asset_rows = []
    view_rows = []

    for selected in selected_rows:
        category = selected["category"]
        uid = selected["uid"]
        asset_dir = args.output_root / category / uid
        view_classes = []
        best_fg_ratio = 0.0
        best_bbox_area_ratio = 0.0
        best_max_dim = 0

        for view in VIEW_NAMES:
            png_path = asset_dir / f"{view}.png"
            image = read_rgb(png_path)
            if image is None:
                view_class = "missing"
                fg_ratio = bbox_width = bbox_height = bbox_area_ratio = ""
            else:
                fg_ratio, bbox_width, bbox_height, bbox_area_ratio = compute_metrics(image)
                view_class = classify_view(fg_ratio, bbox_width, bbox_height, bbox_area_ratio)
                best_fg_ratio = max(best_fg_ratio, fg_ratio)
                best_bbox_area_ratio = max(best_bbox_area_ratio, bbox_area_ratio)
                best_max_dim = max(best_max_dim, bbox_width, bbox_height)

            view_classes.append(view_class)
            view_rows.append(
                {
                    "category": category,
                    "uid": uid,
                    "view": view,
                    "class": view_class,
                    "fg_ratio": fmt(fg_ratio) if fg_ratio != "" else "",
                    "bbox_width": bbox_width,
                    "bbox_height": bbox_height,
                    "bbox_area_ratio": fmt(bbox_area_ratio) if bbox_area_ratio != "" else "",
                    "path": str(png_path),
                }
            )

        new_class = classify_asset(view_classes, best_fg_ratio, best_bbox_area_ratio, best_max_dim)
        asset_rows.append(
            {
                "category": category,
                "uid": uid,
                "previous_class": selected["image_class"],
                "new_class": new_class,
                "best_fg_ratio": fmt(best_fg_ratio),
                "best_bbox_area_ratio": fmt(best_bbox_area_ratio),
                "best_max_dim": best_max_dim,
                "view_classes": ";".join(view_classes),
                "diag_ratio": selected["diag_ratio"],
                "usd_path": selected["usd_path"],
            }
        )

    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    asset_csv = args.analysis_dir / "asset_quality_after.csv"
    view_csv = args.analysis_dir / "view_quality_after.csv"
    with asset_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asset_rows[0].keys()))
        writer.writeheader()
        writer.writerows(asset_rows)
    with view_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(view_rows[0].keys()))
        writer.writeheader()
        writer.writerows(view_rows)

    previous_counts = Counter(row["previous_class"] for row in asset_rows)
    new_counts = Counter(row["new_class"] for row in asset_rows)
    improved_to_ok = sum(row["previous_class"] != "ok" and row["new_class"] == "ok" for row in asset_rows)
    complete = sum(row["new_class"] != "missing" for row in asset_rows)
    summary = [
        "# Selected Rerender Quality Summary",
        "",
        f"assets: {len(asset_rows)}",
        f"complete: {complete}",
        f"improved_to_ok: {improved_to_ok}",
        f"previous_counts: {dict(previous_counts)}",
        f"new_counts: {dict(new_counts)}",
        f"asset_quality_after: {asset_csv}",
        f"view_quality_after: {view_csv}",
    ]
    (args.analysis_dir / "summary.md").write_text("\n".join(summary) + "\n")
    print(f"assets={len(asset_rows)} complete={complete} improved_to_ok={improved_to_ok}")
    print(f"previous_counts={dict(previous_counts)}")
    print(f"new_counts={dict(new_counts)}")
    print(f"wrote={asset_csv}")
    print(f"wrote={view_csv}")


if __name__ == "__main__":
    main()
