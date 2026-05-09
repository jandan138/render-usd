import csv
from pathlib import Path


QUALITY_CSV = Path("docs/tmp/bbox-rerender-selected-validation/analysis_dlc/asset_quality_after.csv")
OUT_CSV = Path("docs/tmp/remaining-cabinet-door-investigation/experiment_assets.csv")

SAMPLE_KEYS = [
    ("cabinet", "05b603614a4ff2f04bfa544a2d85a0bd"),  # all-view tiny
    ("cabinet", "06ba887f18c9cd0fdc34bd23e2c31de2"),  # mostly blank, one tiny plank
    ("cabinet", "0968a1c333825e9d2f912db1d353b0e8"),  # all blank, very sparse plank
    ("cabinet", "1347473d7fe8c041e902558d24c9e375"),  # all blank with non-trivial points
    ("cabinet", "0474a4456e49f2db47f397f00a03b5ca"),  # recovered cabinet control
    ("door", "1f614c5e84cf7ab87a1fc0d1bcf00f40"),  # door tiny/blank
    ("door", "b16b5205214f15c42aed50b3a329326e"),  # door tiny/blank
]


def main() -> None:
    rows = list(csv.DictReader(QUALITY_CSV.open(newline="")))
    by_key = {(row["category"], row["uid"]): row for row in rows}
    selected = []
    for key in SAMPLE_KEYS:
        row = by_key[key]
        selected.append(row)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected[0].keys()))
        writer.writeheader()
        writer.writerows(selected)
    print(f"selected={len(selected)}")
    print(f"wrote={OUT_CSV}")


if __name__ == "__main__":
    main()
