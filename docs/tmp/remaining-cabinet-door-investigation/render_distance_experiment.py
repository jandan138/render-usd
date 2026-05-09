#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path

from isaacsim import SimulationApp


CONFIG = {"headless": True, "anti_aliasing": 4, "multi_gpu": False, "renderer": "PathTracing"}


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(csv_path.open(newline="")))
    if not rows:
        raise ValueError(f"no rows in {csv_path}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Render representative assets with camera distance/elevation variants.")
    parser.add_argument("--selected_csv", type=Path, required=True)
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument("--distance_scale", type=float, required=True)
    parser.add_argument("--elevation", type=float, required=True)
    parser.add_argument("--azimuth_offset", type=float, default=0.0)
    parser.add_argument("--force_double_sided", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    rows = read_rows(args.selected_csv)
    object_usd_paths = [Path(row["usd_path"]) for row in rows]
    output_dirs = [args.output_root / row["category"] / row["uid"] for row in rows]
    for path in object_usd_paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    kit = SimulationApp(CONFIG)
    try:
        import render_usd.core.renderer as renderer_module
        from render_usd.cli import _collect_mdl_paths, _configure_mdl_search_paths
        from render_usd.core.renderer import RenderManager
        from render_usd.core.camera import set_camera_look_at as original_set_camera_look_at
        from render_usd.utils.usd_utils.prim_utils import set_prim_cast_shadow_true as original_set_cast_shadow
        from pxr import UsdGeom

        def scaled_set_camera_look_at(camera, target, distance=0.4, elevation=90.0, azimuth=0.0):
            original_set_camera_look_at(
                camera,
                target,
                distance=max(distance * args.distance_scale, 0.1),
                elevation=args.elevation,
                azimuth=azimuth + args.azimuth_offset,
            )

        renderer_module.set_camera_look_at = scaled_set_camera_look_at

        def force_double_sided_and_shadow(prim):
            original_set_cast_shadow(prim)
            if prim.IsA(UsdGeom.Mesh):
                UsdGeom.Mesh(prim).CreateDoubleSidedAttr(True)
            for child in prim.GetChildren():
                force_double_sided_and_shadow(child)

        if args.force_double_sided:
            renderer_module.set_prim_cast_shadow_true = force_double_sided_and_shadow

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
