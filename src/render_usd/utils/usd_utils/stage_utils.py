from pxr import Usd, UsdGeom
from typing import List
from .prim_utils import IsEmptyXform, IsMeshXform


# Get all mesh prims in the stage, including those inside Xform type prims.
def get_all_mesh_prims(stage, world_node_path="/World"):
    world_prim = stage.GetPrimAtPath(world_node_path)
    mesh_prims = []
    for prim in world_prim.GetAllChildren():
        if prim.IsA(UsdGeom.Mesh):
            mesh_prims.append(prim)
        if prim.IsA(UsdGeom.Xform) and not IsEmptyXform(prim) and IsMeshXform(prim):
            mesh_prims.append(prim)
    return mesh_prims

def get_all_mesh_prims_from_scope(stage, scope_name="Instances"):
    all_mesh_list = []
    instance_scope = stage.GetPrimAtPath(f"/World/{scope_name}")
    for type_scope in instance_scope.GetChildren():
        mesh_list = get_all_mesh_prims(type_scope, f"/World/{scope_name}/{type_scope.GetName()}")
        all_mesh_list.extend(mesh_list)
    return all_mesh_list

def get_all_mesh_prims_from_copy_stage(
    stage, 
    instance_scope_name="Instances", 
    structure_scope_name="Structure",
    ) -> List[Usd.Prim]:
    all_mesh_list = []

    instance_mesh_list = get_all_mesh_prims_from_scope(stage, scope_name=instance_scope_name)
    structure_mesh_list = get_all_mesh_prims_from_scope(stage, scope_name=structure_scope_name)
    
    all_mesh_list.extend(instance_mesh_list)
    all_mesh_list.extend(structure_mesh_list)
    return all_mesh_list



# Remove all empty Xform type prims in the stage.
def remove_empty_xform(stage):
    all_xforms = [prim for prim in stage.Traverse() if prim.IsA(UsdGeom.Xform) and prim.GetPath()!= "/World"]
    all_xforms.sort(key=lambda x: len(x.GetPath().pathString.split("/")), reverse=True)
    for prim in all_xforms:
        if IsEmptyXform(prim): stage.RemovePrim(prim.GetPath())
    return stage

# Maybe all prims are contained in the whole scene, present as a single root xform
def strip_world_prim(stage):
    scene_root = stage.GetPrimAtPath("/World")
    mesh_prims = get_all_mesh_prims(stage)
    if len(mesh_prims) == 1:
        scene_root = mesh_prims[0]
    return scene_root

# Turn on all lighting in the stage.
def switch_all_lights(stage, action="on"):
    action_list = ["on", "off"]
    assert action in action_list, f"Invalid action {action}, should be one of {action_list}"
    light_types = [
        "DistantLight",
        "SphereLight",
        "DiskLight",
        "RectLight",
        "CylinderLight"
    ]

    for prim in stage.Traverse():
        prim_type_name = prim.GetTypeName()
        if prim_type_name in light_types:
            if action == "on":
                UsdGeom.Imageable(prim).MakeVisible()
            else:
                UsdGeom.Imageable(prim).MakeInvisible()
