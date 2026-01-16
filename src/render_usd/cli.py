import argparse
import sys
import os
from pathlib import Path
from isaacsim import SimulationApp

# Configuration for SimulationApp
CONFIG = {"headless": True, "anti_aliasing": 4, "multi_gpu": False, "renderer": "PathTracing"}

def main():
    parser = argparse.ArgumentParser(description="Render USD assets using Isaac Sim")
    subparsers = parser.add_subparsers(dest='command', help='Sub-commands')

    # GRScenes100 command
    parser_gr100 = subparsers.add_parser('grscenes100', help='Render GRScenes-100 dataset')
    parser_gr100.add_argument('--chunk_id', type=int, required=True, help="Chunk ID")
    parser_gr100.add_argument('--chunk_total', type=int, required=True, help="Total chunks")
    parser_gr100.add_argument('--assets_dir', type=str, default=None, help="Assets directory")
    parser_gr100.add_argument('--save_dir', type=str, default=None, help="Save directory. Use 'inplace' to save in same dir as USD.")
    parser_gr100.add_argument('--naming_style', type=str, default="index", choices=["index", "view"], help="Naming convention: index (0,1,...) or view (front,left,...)")

    # GRScenes command
    parser_gr = subparsers.add_parser('grscenes', help='Render GRScenes dataset')
    parser_gr.add_argument('--part', type=int, required=True)
    parser_gr.add_argument('--usd', type=int, required=True)
    parser_gr.add_argument('--scene', type=str, default=None)
    parser_gr.add_argument('--objects_dir', type=str, default=None)
    parser_gr.add_argument('--scene_dir', type=str, default=None)
    parser_gr.add_argument('--naming_style', type=str, default="index", choices=["index", "view"], help="Naming convention")

    # Single file command
    parser_single = subparsers.add_parser('single', help='Render a single USD file')
    parser_single.add_argument('--usd_path', type=str, required=True, help="Path to the USD file")
    parser_single.add_argument('--output_dir', type=str, required=True, help="Directory to save results")
    parser_single.add_argument('--naming_style', type=str, default="index", choices=["index", "view"], help="Naming convention: index (0,1,...) or view (front,left,...)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize Isaac Sim
    kit = SimulationApp(CONFIG)

    # Lazy import to avoid Omni issues before SimulationApp starts
    from render_usd.core.renderer import RenderManager
    from render_usd.config.settings import (
        DEFAULT_GRSCENES100_ASSETS_DIR, DEFAULT_GRSCENES100_SAVE_DIR,
        DEFAULT_GRSCENES_DIR, DEFAULT_GRSCENES_SCENE_DIR
    )
    from natsort import natsorted
    from render_usd.utils.common_utils.path_utils import find_all_files_in_folder

    renderer = RenderManager(kit)

    if args.command == 'grscenes100':
        assets_dir = Path(args.assets_dir) if args.assets_dir else DEFAULT_GRSCENES100_ASSETS_DIR
        
        if args.save_dir == 'inplace':
            save_dir = None
        else:
            save_dir = Path(args.save_dir) if args.save_dir else DEFAULT_GRSCENES100_SAVE_DIR
        
        if not assets_dir.exists():
            print(f"[Error] Assets dir not found: {assets_dir}")
            kit.close()
            return

        # Scan for assets in Category/AssetID/AssetID.usd structure
        all_asset_usds = []
        # First level: Categories
        for cat_path in sorted(assets_dir.iterdir()):
            if not cat_path.is_dir():
                continue
            # Second level: Asset IDs
            for asset_path in sorted(cat_path.iterdir()):
                if not asset_path.is_dir():
                    continue
                
                # Check for USD file named after the directory (AssetID.usd)
                usd_file = asset_path / f"{asset_path.name}.usd"
                if usd_file.exists():
                    all_asset_usds.append(usd_file)

        total_assets = len(all_asset_usds)
        if total_assets == 0:
             print(f"[Error] No assets found in {assets_dir}")
             kit.close()
             return

        chunk_size = (total_assets + args.chunk_total - 1) // args.chunk_total
        start_idx = args.chunk_id * chunk_size
        end_idx = min(start_idx + chunk_size, total_assets)
        
        object_usd_paths = all_asset_usds[start_idx:end_idx]
        
        print(f"[CLI] GRScenes-100 Chunk {args.chunk_id}/{args.chunk_total}: {len(object_usd_paths)} assets ({start_idx}-{end_idx}).")
        
        renderer.render_thumbnail_wo_bg(
            object_usd_paths, 
            save_dir,
            init_azimuth_angle=0,
            sample_number=4,
            show_bbox2d=False,
            naming_style=args.naming_style,
        )

    elif args.command == 'grscenes':
        objects_dir = Path(args.objects_dir) if args.objects_dir else DEFAULT_GRSCENES_DIR
        scene_dir_root = Path(args.scene_dir) if args.scene_dir else DEFAULT_GRSCENES_SCENE_DIR
        
        usd_index = f"part{args.part}/{args.usd}_usd"
        object_dir = objects_dir / usd_index
        
        if args.scene:
            scene_list = [args.scene]
        else:
            if object_dir.exists():
                scene_list = natsorted(os.listdir(object_dir))
            else:
                print(f"[Error] Object dir not found: {object_dir}")
                scene_list = []
            
        for scene_name in scene_list:
            object_usd_dir = object_dir / scene_name
            scene_usd_dir = scene_dir_root / usd_index / scene_name
            source_object_usd_dir = object_usd_dir / "models"
            output_thumbnail_dir = object_usd_dir / "thumbnails"
            thumbnail_wo_bg_dir = output_thumbnail_dir / "multi_views"
            thumbnail_with_bg_dir = output_thumbnail_dir / "multi_views_with_bg"
            
            # Check scene USD
            if not scene_usd_dir.exists():
                 print(f"Scene dir not found: {scene_usd_dir}")
                 continue
                 
            scene_usd_list = find_all_files_in_folder(scene_usd_dir, suffix='.usd')
            scene_copy_usd_path = next((f for f in scene_usd_list if 'copy.usd' in str(f)), None)
            
            if not scene_copy_usd_path:
                print(f"[CLI] {scene_name} has no copy.usd, skip.")
                continue

            # Check object USDs
            if not source_object_usd_dir.exists():
                 print(f"Object models dir not found: {source_object_usd_dir}")
                 continue
            
            # Logic to skip if done
            object_usd_list_length = len(os.listdir(source_object_usd_dir))
            has_rendered_wo_bg = os.path.exists(thumbnail_wo_bg_dir) and len(os.listdir(thumbnail_wo_bg_dir)) == object_usd_list_length
            has_rendered_with_bg = os.path.exists(thumbnail_with_bg_dir) and len(os.listdir(thumbnail_with_bg_dir)) == object_usd_list_length
            
            if not has_rendered_wo_bg:
                os.makedirs(thumbnail_wo_bg_dir, exist_ok=True)
                # Gather USD paths for render_thumbnail_wo_bg
                # Assuming models are in source_object_usd_dir
                # Note: The original code logic was unclear, but assuming we render each model in the folder.
                # Usually source_object_usd_dir contains subfolders per object or USD files?
                # In render_grscenes_main: "source_object_usd_dir = object_usd_dir / 'models'"
                # and "object_usd_list_length = len(os.listdir(source_object_usd_dir))"
                # This implies source_object_usd_dir contains the objects.
                # If they are USD files:
                model_files = [f for f in os.listdir(source_object_usd_dir) if f.endswith('.usd')]
                # Or directories?
                # The original render_thumbnail_wo_bg iterated: "object_name = object_usd_path.parent.name"
                # This implies object_usd_path is .../object_name/something.usd
                # If source_object_usd_dir contains directories of objects, then:
                object_paths = []
                for obj_name in os.listdir(source_object_usd_dir):
                    obj_path = source_object_usd_dir / obj_name
                    if obj_path.is_dir():
                        # Assume instance.usd or similar? Or check for usd file?
                        # Original code didn't show how object_usd_paths was constructed for grscenes mode.
                        # It just passed `object_usd_dir`.
                        # I'll try to find a .usd file in it.
                        usd_files = list(obj_path.glob("*.usd"))
                        if usd_files:
                            object_paths.append(usd_files[0])
                    elif obj_path.suffix == '.usd':
                        object_paths.append(obj_path)

                if object_paths:
                    renderer.render_thumbnail_wo_bg(object_paths, thumbnail_wo_bg_dir, naming_style=args.naming_style)

            if not has_rendered_with_bg:
                os.makedirs(thumbnail_with_bg_dir, exist_ok=True)
                renderer.render_thumbnail_with_bg(scene_copy_usd_path, object_usd_dir, thumbnail_with_bg_dir)

    elif args.command == 'single':
        usd_path = Path(args.usd_path)
        output_dir = Path(args.output_dir)
        
        if not usd_path.exists():
            print(f"[Error] USD file not found: {usd_path}")
            kit.close()
            return
            
        print(f"[CLI] Rendering single file: {usd_path}")
        renderer.render_thumbnail_wo_bg(
            [usd_path], 
            output_dir, 
            init_azimuth_angle=0, 
            sample_number=4, 
            show_bbox2d=False,
            naming_style=args.naming_style
        )

    kit.close()

if __name__ == "__main__":
    main()
