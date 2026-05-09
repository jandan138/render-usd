import argparse
import csv
from pathlib import Path

from isaacsim import SimulationApp


CONFIG = {"headless": True, "anti_aliasing": 4, "multi_gpu": False, "renderer": "PathTracing"}


def parse_args():
    parser = argparse.ArgumentParser(description="Render a selected GRScenes recommended subset into docs/tmp.")
    parser.add_argument("--selected_csv", type=Path, required=True)
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    rows = list(csv.DictReader(args.selected_csv.open(newline="")))
    if not rows:
        raise ValueError("selected_csv has no rows")

    object_usd_paths = [Path(row["usd_path"]) for row in rows]
    output_dirs = [args.output_root / row["category"] / row["uid"] for row in rows]
    for path in object_usd_paths:
        if not path.is_file():
            raise FileNotFoundError(path)

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
                naming_style="view",
                overwrite=args.overwrite,
            )
        finally:
            renderer.cleanup()
    finally:
        kit.close()


if __name__ == "__main__":
    main()
