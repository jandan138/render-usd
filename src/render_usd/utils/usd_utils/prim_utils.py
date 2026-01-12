import numpy as np
from pxr import Usd, UsdGeom, Gf
from typing import List, Tuple


#==============================================================================
#                             PARSING UTILS
#==============================================================================

def to_list(data):
    res = []
    if data is not None:
        res = [_ for _ in data]
    return res

# Recursively parse the prim tree to get all points, faceVertexCounts, and faceVertexIndices
# - points: Nx3
# - faceVertexCounts: 1xM, M is the number of faces
# - faceVertexIndices: sum(faceVertexCounts), points indices for each face
def recursive_parse(prim: Usd.Prim) -> Tuple[List[Gf.Vec3f], List[int], List[int]]:

    points_total = []
    faceVertexCounts_total = []
    faceVertexIndices_total = []

    if prim.IsA(UsdGeom.Mesh):
        prim_imageable = UsdGeom.Imageable(prim)
        xform_world_transform = np.array(
            prim_imageable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        )

        points = prim.GetAttribute("points").Get()
        faceVertexCounts = prim.GetAttribute("faceVertexCounts").Get()
        faceVertexIndices = prim.GetAttribute("faceVertexIndices").Get()
        faceVertexCounts = to_list(faceVertexCounts)
        faceVertexIndices = to_list(faceVertexIndices)
        points = to_list(points)
        points = np.array(points)  # Nx3
        ones = np.ones((points.shape[0], 1))  # Nx1
        points_h = np.hstack([points, ones])  # Nx4
        points_transformed_h = np.dot(points_h, xform_world_transform)  # Nx4
        points_transformed = points_transformed_h[:, :3] / points_transformed_h[:, 3][:, np.newaxis]  # Nx3
        points = points_transformed.tolist()
        points = np.array(points)

        if np.isnan(points).any():
            # There is "nan" in points
            print("[GRGenerator: Recursive Parse] Found NaN in points, performing clean-up...")
            nan_mask = np.isnan(points).any(axis=1)  
            valid_points_mask = ~nan_mask  
            points_clean = points[valid_points_mask].tolist()
            faceVertexIndices = np.array(faceVertexIndices).reshape(-1, 3)
            old_to_new_indices = np.full(points.shape[0], -1)
            old_to_new_indices[valid_points_mask] = np.arange(np.sum(valid_points_mask))
            valid_faces_mask = np.all(old_to_new_indices[faceVertexIndices] != -1, axis=1)
            faceVertexIndices_clean = old_to_new_indices[faceVertexIndices[valid_faces_mask]].flatten().tolist()
            faceVertexCounts_clean = np.array(faceVertexCounts)[valid_faces_mask].tolist()
            base_num = len(points_total)
            faceVertexIndices_total.extend((base_num + np.array(faceVertexIndices_clean)).tolist())
            faceVertexCounts_total.extend(faceVertexCounts_clean)
            points_total.extend(points_clean)
        else:
            base_num = len(points_total)
            faceVertexIndices = np.array(faceVertexIndices)
            faceVertexIndices_total.extend((base_num + faceVertexIndices).tolist())
            faceVertexCounts_total.extend(faceVertexCounts)
            points_total.extend(points)

    children = prim.GetChildren()
    for child in children:
        child_points, child_faceVertexCounts, child_faceVertexIndices = recursive_parse(child)
        base_num = len(points_total)
        child_faceVertexIndices = np.array(child_faceVertexIndices)
        faceVertexIndices_total.extend((base_num + child_faceVertexIndices).tolist())
        faceVertexCounts_total.extend(child_faceVertexCounts)
        points_total.extend(child_points)

    return (
        points_total,
        faceVertexCounts_total,
        faceVertexIndices_total,
    )



#==============================================================================
#                             CHECK UTILS
#==============================================================================

# Check if a Xform type prim is empty, 
# the empty xform is generated because the connector does not support exporting this type of object.
def IsEmptyXform(xform_prim):
    assert xform_prim.IsA(UsdGeom.Xform)
    return len(xform_prim.GetChildren()) == 0

# Check if a Xform type prim is a mesh, because the scenes may exist xforms composed entirely of lights.
# The Xform type may be structured as follows:
# - All elements are lights,            e.g. a complex lighting group.
# - All elements are meshes,            e.g. a tabel with a tabletop and its legs.
# - Consists of both lights and meshes, e.g. a cabinet with structure and its display light.
def IsMeshXform(prim):
    if prim.IsA(UsdGeom.Mesh):
        return True
    children = prim.GetChildren()
    for child in children:
        if IsMeshXform(child):
            return True
    return False


#==============================================================================
#                             COMPUTE UTILS
#==============================================================================
def compute_bbox(prim: Usd.Prim) -> np.ndarray:
    """
    Compute Bounding Box using ComputeWorldBound at UsdGeom.Imageable

    Args:
        prim: A prim to compute the bounding box.

    Returns: 
        bound_range: A numpy array, [(min_x, min_y, min_z), (max_x, max_y, max_z)]
    """
    imageable: UsdGeom.Imageable = UsdGeom.Imageable(prim)
    time = Usd.TimeCode.Default()
    bound = imageable.ComputeWorldBound(time, UsdGeom.Tokens.default_)
    bound_range = bound.ComputeAlignedBox()
    bbox_min = bound_range.min
    bbox_max = bound_range.max
    bound_range = np.array([bbox_min, bbox_max])
    return bound_range
            
#==============================================================================
#                              ATTRIBUTE UTILS
#==============================================================================
def visiblePrims(prim: Usd.Prim) -> None:
    for child in prim.GetChildren():
        UsdGeom.Imageable(child).MakeVisible()
        visiblePrims(child)
    return

def print_prim_attributes(prim: Usd.Prim, indent: int = 0) -> None:
    prefix = "  " * indent
    print(f"{prefix}Prim: {prim.GetPath()} (Type: {prim.GetTypeName()})")
    
    attributes = prim.GetAttributes()
    for attribute in attributes:
        attribute_name = attribute.GetName()
        print(f"{prefix}  - {attribute_name}")
    
    children = prim.GetChildren()
    for child in children:
        print_prim_attributes(child, indent + 1)


def set_prim_cast_shadow_true(prim: Usd.Prim) -> None:

    if prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Xform):
        attributes = prim.GetAttributes()
        for attribute in attributes:
            attribute_name = attribute.GetName()
            if attribute_name == "primvars:doNotCastShadows":
                # print(f"[GRGenerator: Set Cast Shadow] Prim {prim.GetPath()} is setted with castShadow True. \
                #         Previously: {not attribute.Get()}")
                attribute.Set(False)
                return

        children = prim.GetChildren()
        for child in children:
            set_prim_cast_shadow_true(child)



if __name__ == "__main__":
    stage = Usd.Stage.Open("/cpfs/user/caopeizhou/data/GRScenes/instances/part1/101_usd/0001/models/Group6_splited/instance.usd")
    prim = stage.GetPrimAtPath("/Root/Instance")
    set_prim_cast_shadow_true(prim)
