import csv
from collections import Counter, defaultdict
from pathlib import Path


SOURCE = Path("docs/tmp/bbox-rerender-manifest-full/bbox_rerender_recommended.csv")
OUT_DIR = Path("docs/tmp/bbox-rerender-selected-validation")
TARGET_PER_CLASS = 12
TARGET_TOTAL = 36
CLASS_ORDER = ("blank", "tiny", "suspicious")
PREFERRED_CATEGORIES = (
    "basket",
    "cabinet",
    "cart",
    "desk",
    "dish_washer",
    "door",
    "electric_cooker",
    "faucet",
    "hearth",
    "microwave",
    "night_stand",
    "oven",
    "pan",
    "pot",
    "refrigerator",
    "table",
    "trash_can",
    "washing_machine",
)


def ratio_bin(row):
    ratio = float(row["diag_ratio"])
    if ratio < 10:
        return "5-10x"
    if ratio < 100:
        return "10-100x"
    if ratio < 1_000_000:
        return "100-1e6x"
    return "1e6x+"


def max_dim_bin(row):
    value = int(float(row.get("best_max_dim") or 0))
    if value == 0:
        return "0"
    if value < 64:
        return "1-63"
    if value < 128:
        return "64-127"
    if value < 256:
        return "128-255"
    return "256+"


def sort_key(row):
    category_rank = PREFERRED_CATEGORIES.index(row["category"]) if row["category"] in PREFERRED_CATEGORIES else len(PREFERRED_CATEGORIES)
    return (
        category_rank,
        ratio_bin(row),
        max_dim_bin(row),
        row["category"],
        row["uid"],
    )


def select_for_class(rows, image_class, target):
    candidates = sorted((row for row in rows if row["image_class"] == image_class), key=sort_key)
    selected = []
    used_categories = Counter()
    used_ratio_bins = Counter()
    used_dim_bins = Counter()

    while candidates and len(selected) < target:
        best_index = None
        best_score = None
        for index, row in enumerate(candidates):
            score = (
                used_categories[row["category"]],
                used_ratio_bins[ratio_bin(row)],
                used_dim_bins[max_dim_bin(row)],
                sort_key(row),
            )
            if best_score is None or score < best_score:
                best_index = index
                best_score = score
        row = candidates.pop(best_index)
        row = dict(row)
        row["ratio_bin"] = ratio_bin(row)
        row["max_dim_bin"] = max_dim_bin(row)
        selected.append(row)
        used_categories[row["category"]] += 1
        used_ratio_bins[row["ratio_bin"]] += 1
        used_dim_bins[row["max_dim_bin"]] += 1

    return selected


def main():
    rows = list(csv.DictReader(SOURCE.open(newline="")))
    selected = []
    for image_class in CLASS_ORDER:
        selected.extend(select_for_class(rows, image_class, TARGET_PER_CLASS))

    if len(selected) != TARGET_TOTAL:
        raise RuntimeError(f"selected {len(selected)} rows, expected {TARGET_TOTAL}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "selected_assets.csv"
    txt_path = OUT_DIR / "selected_usds.txt"
    fieldnames = list(selected[0].keys())
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)
    txt_path.write_text("\n".join(row["usd_path"] for row in selected) + "\n")

    print(f"selected={len(selected)}")
    print("by_class", dict(Counter(row["image_class"] for row in selected)))
    print("by_category", dict(Counter(row["category"] for row in selected).most_common()))
    print("by_ratio_bin", dict(Counter(row["ratio_bin"] for row in selected).most_common()))
    print("by_max_dim_bin", dict(Counter(row["max_dim_bin"] for row in selected).most_common()))
    print(f"wrote={csv_path}")
    print(f"wrote={txt_path}")


if __name__ == "__main__":
    main()
