import os
import cv2
import numpy as np
from tqdm import tqdm
from pathlib import Path
from natsort import natsorted
from typing import Tuple, List, Optional

import omni
import omni.kit.commands
from pxr import Usd, UsdLux
from omni.isaac.core.utils.stage import add_reference_to_stage
from omni.isaac.core.utils.prims import delete_prim, create_prim
from omni.isaac.core.utils.semantics import add_update_semantics, remove_all_semantics

from render_usd.utils.common_utils.path_utils import find_all_files_in_folder
from render_usd.utils.common_utils.sim_utils import init_world, set_camera_look_at, init_camera, setup_camera, get_src
from render_usd.utils.common_utils.images_utils import draw_bbox2d
from render_usd.utils.usd_utils.prim_utils import compute_bbox, set_prim_cast_shadow_true
from render_usd.utils.usd_utils.stage_utils import get_all_mesh_prims_from_scope, switch_all_lights
from render_usd.utils.usd_utils.mdl_utils import fix_mdls
from render_usd.config.settings import DEFAULT_MDL_PATH, DEFAULT_ENVIRONMENT_PATH

class RenderManager:
    def __init__(self, app=None):
        self.app = app
        self.world = init_world()

    def compute_2d_bbox_area(self, bbox2d_data: Tuple[int, float, float, float, float, float]) -> float:
        width = bbox2d_data[3] - bbox2d_data[1]
        height = bbox2d_data[4] - bbox2d_data[2]
        area = width * height
        return area

    def compute_2d_bbox_area_ratio(
        self,
        bbox2d_tight: Tuple[int, float, float, float, float, float], 
        bbox2d_loose: Tuple[int, float, float, float, float, float]
    ) -> float:
        tight_area = self.compute_2d_bbox_area(bbox2d_tight)
        loose_area = self.compute_2d_bbox_area(bbox2d_loose)
        if loose_area > 0:
            return tight_area / loose_area
        else:
            return 0.0

    def render_thumbnail_wo_bg(
        self,
        object_usd_paths: List[Path], 
        thumbnail_wo_bg_dir: Path, 
        show_bbox2d=True,
        sample_number=4,
        init_azimuth_angle=0,
    ):
        # Light settings
        # world = init_world() # Already inited in __init__
        if not self.world:
            self.world = init_world()
            
        # Try to load environment, fallback to Dome Light if failed or file missing
        env_path = str(DEFAULT_ENVIRONMENT_PATH)
        if os.path.exists(env_path):
             add_reference_to_stage(env_path, "/World/environment")
        else:
             print(f"[RenderManager] Environment file not found at {env_path}, creating default Dome Light.")
             stage = omni.usd.get_context().get_stage()
             dome_light = UsdLux.DomeLight.Define(stage, "/World/default_dome_light")
             dome_light.CreateIntensityAttr(1000)
             dome_light.CreateTextureFormatAttr(UsdLux.Tokens.latlong)
        
        # Camera settings
        cameras = []
        for i in range(sample_number):
            camera = init_camera(f"camera_{i}", image_width=512, image_height=512)
            setup_camera(camera, with_bbox2d=show_bbox2d)
            cameras.append(camera)

        for object_usd_path in tqdm(object_usd_paths, desc="Rendering objects"):
            object_usd_path = Path(object_usd_path)
            object_name = object_usd_path.parent.name
            save_dir = thumbnail_wo_bg_dir / object_name 
            has_rendered = os.path.exists(save_dir) and len(os.listdir(save_dir)) == sample_number
            if has_rendered:
                continue
            
            print(f"Rendering: {object_usd_path}")
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
                
            for _ in range(100): # Reduced from 1000 for efficiency if possible, but keeping logic similar. Original: 1000
                 self.world.step(render=False)
            for _ in range(8):
                 self.world.step(render=True)
                 
            os.makedirs(save_dir, exist_ok=True)
            for idx, camera in enumerate(cameras):
                rgb = get_src(camera, "rgb")
                
                if show_bbox2d:
                    bbox2d = get_src(camera, "bbox2d_tight")
                    try:
                        bbox2d_data = bbox2d[0][0]  # get the first row data
                        rgb = draw_bbox2d(rgb, bbox2d_data)
                    except:
                        print(f"[RenderManager: Render Thumbnail Without Background] {object_name} {idx} bbox2d is not valid due to the specific aspect.")
                    cv2.imwrite(f"{save_dir}/{object_name}_{idx}_bbox2d.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
                else:
                    cv2.imwrite(f"{save_dir}/{object_name}_{idx}.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
            delete_prim(show_prim_path)

    def render_thumbnail_with_bg(self, scene_usd_path, object_usd_dir, thumbnail_with_bg_dir, show_bbox2d=True):
        # Auto exposure
        omni.kit.commands.execute('ChangeSetting', path='/rtx/post/histogram/enabled', value=True)
        omni.kit.commands.execute('ChangeSetting', path='/rtx/post/histogram/whiteScale', value=10.0)
        
        # World settings
        if not self.world:
            self.world = init_world()
            
        fix_mdls(str(scene_usd_path), str(DEFAULT_MDL_PATH))
        add_reference_to_stage(str(scene_usd_path), "/World/scene")
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
        
        if not os.path.exists(object_models_dir):
             print(f"[RenderManager] Models dir not found: {object_models_dir}")
             return

        extracted_object_names = natsorted(os.listdir(object_models_dir))
        
        for index, mesh_prim in enumerate(tqdm(instance_mesh_prims, desc="Rendering scene instances")):
            mesh_prim_name = mesh_prim.GetName()
            if mesh_prim_name not in extracted_object_names:
                print(f"[RenderManager: Render Thumbnail With Background] {mesh_prim_name} is not extracted, skip.")
                continue
                
            mesh_dir = thumbnail_with_bg_dir / mesh_prim.GetName()
            if os.path.exists(mesh_dir) and len(os.listdir(mesh_dir)) > 0:
                continue
                
            set_prim_cast_shadow_true(mesh_prim)
            add_update_semantics(mesh_prim, semantic_label=f"instance_{index}", type_label="class")
            bbox_min, bbox_max = compute_bbox(mesh_prim)
            center = (bbox_min + bbox_max) / 2
            distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
            
            for i in range(sample_number):
                azimuth = 30 + i * 360 / (sample_number / 2)
                elevation = 35 if i < sample_number / 2 else -35
                set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)
                
            for _ in range(100): # Reduced from 1000
                 self.world.step(render=False)
            for _ in range(8):
                 self.world.step(render=True)
                 
            os.makedirs(mesh_dir, exist_ok=True)
            all_top_views_valid = True
            
            for idx, camera in enumerate(cameras):
                rgb = get_src(camera, "rgb")
                need_save = True
                
                if show_bbox2d:
                    bbox2d_tight = get_src(camera, "bbox2d_tight")[0]
                    bbox2d_loose = get_src(camera, "bbox2d_loose")[0]
                    
                    is_detected = len(bbox2d_tight) > 0 and len(bbox2d_loose) > 0
                    if is_detected:
                        bbox2d_tight_data = bbox2d_tight[0]  # get the first row data
                        bbox2d_loose_data = bbox2d_loose[0]  # get the first row data
                        area_ratio = self.compute_2d_bbox_area_ratio(bbox2d_tight_data, bbox2d_loose_data)
                        if area_ratio >= 0.8:
                            rgb = draw_bbox2d(rgb, bbox2d_tight_data)
                        else:
                            need_save = False
                    else:
                        print(f"[RenderManager: Render Thumbnail With Background] {mesh_prim.GetName()}_{idx} bbox2d is not detected.")
                        need_save = False  
                        if idx < sample_number / 2:
                            all_top_views_valid = False
                            
                    if not all_top_views_valid and idx >= sample_number / 2:
                        need_save = False
                        
                if need_save:
                    cv2.imwrite(f"{mesh_dir}/{mesh_prim.GetName()}_with_bg_{idx}.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
                    
            remove_all_semantics(mesh_prim)
