import omni
import os
from pxr import Usd, UsdLux
from omni.isaac.core import World
from omni.isaac.core.utils.semantics import add_update_semantics
from omni.isaac.core.utils.stage import add_reference_to_stage
from typing import Dict, Optional

from render_usd.utils.usd_utils.stage_utils import get_all_mesh_prims, get_all_mesh_prims_from_scope
from render_usd.config.settings import DEFAULT_ENVIRONMENT_PATH

#==============================================================================
#                                INIT/SETUP WORLD
#==============================================================================

def init_world(
    stage_units_in_meters: float = 1.0,
    physics_dt: float = 0.01,
    rendering_dt: float = 0.01,
) -> World:
    world = World(
        stage_units_in_meters=stage_units_in_meters,
        physics_dt=physics_dt,
        rendering_dt=rendering_dt,
    )
    world.reset()
    return world

def setup_environment(env_path: Optional[str] = None):
    """
    Load environment file or create a default Dome Light if file not found.
    """
    if env_path is None:
        env_path = str(DEFAULT_ENVIRONMENT_PATH)
        
    if os.path.exists(env_path):
         add_reference_to_stage(env_path, "/World/environment")
         print(f"[Scene] Loaded environment from {env_path}")
    else:
         print(f"[Scene] Environment file not found at {env_path}, creating default Dome Light.")
         stage = omni.usd.get_context().get_stage()
         dome_light = UsdLux.DomeLight.Define(stage, "/World/default_dome_light")
         dome_light.CreateIntensityAttr(1000)
         dome_light.CreateTextureFormatAttr(UsdLux.Tokens.latlong)

def setup_instance_scene(stage: Usd.Stage) -> None:
    object_mesh_prims = get_all_mesh_prims(stage, world_node_path="/World/scene")
    for idx, prim in enumerate(object_mesh_prims):
        add_update_semantics(prim, semantic_label=f"instance_{idx}", type_label="class")
        print(f"[Scene: Setup Instance] Prim {prim.GetName()} is setted with semantic label 'instance_{idx}'.")
    
def setup_instance_copy_scene(stage: Usd.Stage) -> None:
    object_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Instances")
    structure_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure")
    all_mesh_prims = object_mesh_prims + structure_mesh_prims
    for idx, prim in enumerate(all_mesh_prims):
        add_update_semantics(prim, semantic_label=f"instance_{idx}", type_label="class")
        print(f"[Scene: Setup Instance Copy] Prim {prim.GetName()} is setted with semantic label 'instance_{idx}'.")

def setup_semantic_object_copy_scene(stage: Usd.Stage, category_annotation: Dict[str, str]) -> None:
    object_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Instances")
    for prim in object_mesh_prims:
        prim_name = prim.GetName()
        semantic_label = category_annotation[prim_name]
        add_update_semantics(prim, semantic_label=semantic_label, type_label="class")
        print(f"[Scene: Setup Semantic] Prim {prim.GetName()} is setted with semantic label '{semantic_label}'.")

def setup_semantic_scene_copy(stage: Usd.Stage, object_annotation: Dict[str, str]) -> None:
    object_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Instances")
    wall_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure/Wall")
    floor_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure/Floor")
    ceiling_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure/Ceiling")
    background_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure/BgWall")
    
    for prim in object_mesh_prims:
        prim_name = prim.GetName()
        semantic_label = object_annotation[prim_name]
        add_update_semantics(prim, semantic_label=semantic_label, type_label="class")
        
    for wall_prim in wall_mesh_prims:
        add_update_semantics(wall_prim, semantic_label="wall", type_label="class")
    for floor_prim in floor_mesh_prims:
        add_update_semantics(floor_prim, semantic_label="floor", type_label="class")
    for ceiling_prim in ceiling_mesh_prims:
        add_update_semantics(ceiling_prim, semantic_label="ceiling", type_label="class")
    for background_prim in background_mesh_prims:
        add_update_semantics(background_prim, semantic_label="background", type_label="class")
