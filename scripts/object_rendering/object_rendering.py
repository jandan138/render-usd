# Rendering the object to the thumbnail images and thumbnails with their corresponding background.
# Input: 1. the object usd file. 2. the usd file after instance segmentation. 
# Output: 1. the thumbnail images. 2. the thumbnails with their corresponding background.
import argparse
import os
import cv2
import numpy as np
from tqdm import tqdm
from pathlib import Path
from natsort import natsorted
from typing import Tuple, List
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True, \
                                "anti_aliasing": 4, \
                                "multi_gpu": False, \
                                "renderer": "PathTracing"})

import omni
from pxr import Usd
from omni.isaac.core.utils.stage import add_reference_to_stage                          # type: ignore
from omni.isaac.core.utils.prims import delete_prim, create_prim                        # type: ignore
from omni.isaac.core.utils.semantics import add_update_semantics, remove_all_semantics  # type: ignore
from utils.common_utils.path_utils import find_all_files_in_folder
from utils.common_utils.sim_utils import init_world, set_camera_look_at, init_camera, setup_camera, get_src
from utils.common_utils.images_utils import draw_bbox2d
from utils.usd_utils.prim_utils import compute_bbox, set_prim_cast_shadow_true
from utils.usd_utils.stage_utils import get_all_mesh_prims_from_scope, switch_all_lights
from utils.usd_utils.mdl_utils import fix_mdls



DEFAULT_MDL_PATH = "../assets/materials/default.mdl"
DEFAULT_ENVIRONMENT_PATH = "../assets/environments/background.usd"

def render_thumbnail_wo_bg(
    object_usd_paths: List[Path], 
    thumbnail_wo_bg_dir: Path, 
    show_bbox2d=True,
    sample_number=4,
    init_azimuth_angle=0,
):
    # Light settings
    world = init_world()
    add_reference_to_stage(DEFAULT_ENVIRONMENT_PATH, "/World/environment")
    # Camera settings
    cameras = []
    for i in range(sample_number):
        camera = init_camera(f"camera_{i}", image_width=512, image_height=512)
        setup_camera(camera, with_bbox2d=show_bbox2d)
        cameras.append(camera)

    for object_usd_path in tqdm(object_usd_paths):
        object_usd_path = Path(object_usd_path)
        object_name = object_usd_path.parent.name
        save_dir = thumbnail_wo_bg_dir / object_name 
        has_rendered = os.path.exists(save_dir) and len(os.listdir(save_dir)) == sample_number
        if has_rendered:
            continue
        print(object_usd_path)
        show_prim_path = "/World/Show"
        usd_prim = create_prim(show_prim_path, position=(0, 0, 0), scale=(1, 1, 1), usd_path=str(object_usd_path))
        set_prim_cast_shadow_true(usd_prim)
        add_update_semantics(usd_prim, semantic_label="instance", type_label="class")
        bbox_min, bbox_max = compute_bbox(usd_prim)
        center = (bbox_min + bbox_max) / 2
        
        for i in range(sample_number):
            azimuth = init_azimuth_angle + i * 360 / sample_number
            elevation = 35
            distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
            set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)
            
        for _ in range(1000):
            world.step(render=False)
        for _ in range(8):
            world.step(render=True)
        os.makedirs(save_dir, exist_ok=True)
        for idx, camera in enumerate(cameras):
            rgb = get_src(camera, "rgb")
            
            if show_bbox2d:
                bbox2d = get_src(camera, "bbox2d_tight")
                # print(bbox2d)
                # bbox2d: (array with fields, dict)
                try:
                    bbox2d_data = bbox2d[0][0]  # get the first row data
                    rgb = draw_bbox2d(rgb, bbox2d_data)
                except:
                    print(f"[GRGenerator: Render Thumbnail Without Background] {object_name} {idx} bbox2d is not valid due to the specific aspect.")
                cv2.imwrite(f"{save_dir}/{object_name}_{idx}_bbox2d.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
            else:
                cv2.imwrite(f"{save_dir}/{object_name}_{idx}.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
        delete_prim(show_prim_path)

def compute_2d_bbox_area(bbox2d_data: Tuple[int, float, float, float, float, float]) -> float:
    width = bbox2d_data[3] - bbox2d_data[1]
    height = bbox2d_data[4] - bbox2d_data[2]
    area = width * height
    return area

def compute_2d_bbox_area_ratio(
    bbox2d_tight    : Tuple[int, float, float, float, float, float], 
    bbox2d_loose: Tuple[int, float, float, float, float, float]
    ) -> float:
    tight_area = compute_2d_bbox_area(bbox2d_tight)
    loose_area = compute_2d_bbox_area(bbox2d_loose)
    # print(f"[DEBUG] tight_area: {tight_area}, loose_area: {loose_area}")
    if loose_area > 0:
        return tight_area / loose_area
    else:
        return 0.0
        
def render_thumbnail_with_bg(scene_usd_path, object_usd_dir, thumbnail_with_bg_dir, show_bbox2d=True):
    # Auto exposure
    omni.kit.commands.execute('ChangeSetting', path='/rtx/post/histogram/enabled', value=True)
    omni.kit.commands.execute('ChangeSetting', path='/rtx/post/histogram/whiteScale', value=10.0)
    # World settings
    world = init_world()
    fix_mdls(scene_usd_path, DEFAULT_MDL_PATH)
    add_reference_to_stage(scene_usd_path, "/World/scene")
    stage = omni.usd.get_context().get_stage()
    switch_all_lights(stage, 'on')
    # Camera settings
    sample_number = 3 + 3
    cameras = []
    for i in range(sample_number):
        camera = init_camera(f"camera_{i}", image_width=600, image_height=450)
        setup_camera(camera, with_bbox2d=show_bbox2d, focal_length=9.0)
        cameras.append(camera)
    instance_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Instances")
    object_models_dir = object_usd_dir / "models"
    extracted_object_names = natsorted(os.listdir(object_models_dir))
    for index, mesh_prim in enumerate(tqdm(instance_mesh_prims)):
        # # debug
        # if mesh_prim.GetName() != "___1986702865_1":
        #     continue
        mesh_prim_name = mesh_prim.GetName()
        if mesh_prim_name not in extracted_object_names:
            print(f"[GRGenerator: Render Thumbnail With Background] {mesh_prim_name} is not extracted, skip.")
            continue
        mesh_dir = thumbnail_with_bg_dir / mesh_prim.GetName()
        if os.path.exists(mesh_dir) and len(os.listdir(mesh_dir)) > 0:
            continue
        set_prim_cast_shadow_true(mesh_prim)
        add_update_semantics(mesh_prim, semantic_label=f"instance_{index}", type_label="class")
        bbox_min, bbox_max = compute_bbox(mesh_prim)
        center = (bbox_min + bbox_max) / 2
        distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
        print(f"[DEBUG] {mesh_prim.GetName()} bbox_min: {bbox_min}, bbox_max: {bbox_max}, center: {center}, distance: {distance}")
        for i in range(sample_number):
            azimuth = 30 + i * 360 / (sample_number / 2)
            elevation = 35 if i < sample_number / 2 else -35
            set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)
        for _ in range(1000):
            world.step(render=False)
        for _ in range(8):
            world.step(render=True)
        os.makedirs(thumbnail_with_bg_dir / mesh_prim.GetName(), exist_ok=True)
        all_top_views_valid = True
        for idx, camera in enumerate(cameras):
            rgb = get_src(camera, "rgb")
            need_save = True
            if show_bbox2d:
                bbox2d_tight = get_src(camera, "bbox2d_tight")[0]
                bbox2d_loose = get_src(camera, "bbox2d_loose")[0]
                print(f"[DEBUG] bbox2d_tight: {bbox2d_tight}, bbox2d_loose: {bbox2d_loose}")
                is_detected = len(bbox2d_tight) > 0 and len(bbox2d_loose) > 0
                if is_detected:
                    bbox2d_tight_data = bbox2d_tight[0]  # get the first row data
                    bbox2d_loose_data = bbox2d_loose[0]  # get the first row data
                    area_ratio = compute_2d_bbox_area_ratio(bbox2d_tight_data, bbox2d_loose_data)
                    if area_ratio >= 0.8:
                        rgb = draw_bbox2d(rgb, bbox2d_tight_data)
                    else:
                        need_save = False
                else:
                    print(f"[GRGenerator: Render Thumbnail With Background] {mesh_prim.GetName()}_{idx} bbox2d is not detected.")
                    need_save = False  
                    if idx < sample_number / 2:
                        all_top_views_valid = False
                if not all_top_views_valid and idx >= sample_number / 2:
                    need_save = False
            if need_save:
                cv2.imwrite(f"{mesh_dir}/{mesh_prim.GetName()}_with_bg_{idx}.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
        remove_all_semantics(mesh_prim)



def render_grscenes_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects_dir", default='/cpfs/user/caopeizhou/data/GRScenes/instances')
    parser.add_argument("--scene_dir", default='/cpfs/user/caopeizhou/projects/GRGenerator/_scenes/GRScenes')    # Must be absolute path.
    parser.add_argument('--part', type=int, default=1, required=True)
    parser.add_argument('--usd', type=int, required=True)
    parser.add_argument("--scene", type=str, default=None)
    args = parser.parse_args()
    usd_index   = f"part{args.part}/{args.usd}_usd"
    objects_dir = Path(args.objects_dir)
    scene_dir   = Path(args.scene_dir)
    object_dir = objects_dir / usd_index
    if args.scene:
        scene_list = [args.scene]
    else:
        scene_list = natsorted(os.listdir(object_dir))

    for scene_name in scene_list:
        object_usd_dir        = object_dir / scene_name
        scene_usd_dir         = scene_dir / usd_index / scene_name
        source_object_usd_dir = object_usd_dir / "models"
        output_thumbnail_dir  = object_usd_dir / "thumbnails"
        thumbnail_wo_bg_dir   = output_thumbnail_dir / "multi_views" 
        thumbnail_with_bg_dir = output_thumbnail_dir / "multi_views_with_bg"

        # Check the source usd file.
        scene_usd_list = find_all_files_in_folder(scene_usd_dir, suffix='.usd')
        scene_copy_usd_path = [f for f in scene_usd_list if 'copy.usd' in f][0]
        print(scene_copy_usd_path)
        if scene_copy_usd_path is None:
            print(f"[GRGenerator: Render Objects] {scene_name} has {len(scene_usd_list)} usd files, skip.")
            continue

        # Check the source object usd file.
        object_usd_list_length  = len(os.listdir(source_object_usd_dir))


        has_rendered_thumbnail_wo_bg = os.path.exists(thumbnail_wo_bg_dir) and \
                                       len(os.listdir(thumbnail_wo_bg_dir)) == object_usd_list_length
        has_rendered_thumbnail_with_bg = os.path.exists(thumbnail_with_bg_dir) and \
                                       len(os.listdir(thumbnail_with_bg_dir)) == object_usd_list_length

        if not has_rendered_thumbnail_wo_bg:
            os.makedirs(thumbnail_wo_bg_dir, exist_ok=True)
            render_thumbnail_wo_bg(object_usd_dir, thumbnail_wo_bg_dir)
        if not has_rendered_thumbnail_with_bg:
            os.makedirs(thumbnail_with_bg_dir, exist_ok=True)
            render_thumbnail_with_bg(scene_copy_usd_path, object_usd_dir, thumbnail_with_bg_dir)

def render_grscenes100_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunk_id', type=int, required=True)
    parser.add_argument('--chunk_total', type=int, required=True)
    args = parser.parse_args()
    
    grscenes100_assets_dir = Path("/cpfs/user/caopeizhou/data/GRScenes-100/Asset_Library_all")
    save_dir = Path("/oss-caopeizhou/data/GRScenes-100/all_assets_renderings")
    grscenes100_assets = natsorted(os.listdir(grscenes100_assets_dir))
    
    total_assets = len(grscenes100_assets)
    chunk_size = (total_assets + args.chunk_total - 1) // args.chunk_total
    start_idx = args.chunk_id * chunk_size
    end_idx = min(start_idx + chunk_size, total_assets)
    
    grscenes100_assets_chunk = grscenes100_assets[start_idx:end_idx]
    
    object_usd_paths = []
    for asset in grscenes100_assets_chunk:
        object_usd_paths.append(grscenes100_assets_dir / asset / "instance.usd")
    
    print(f"[GRGenerator: Render GRScenes-100] Chunk {args.chunk_id}/{args.chunk_total}: {len(object_usd_paths)} assets to render (index {start_idx} to {end_idx-1}).")
    
    render_thumbnail_wo_bg(
        object_usd_paths, 
        save_dir,
        init_azimuth_angle=0,
        sample_number=4,
        show_bbox2d=False,
    )



if __name__ == '__main__':
    # render_grscenes_main()
    render_grscenes100_main()


        


