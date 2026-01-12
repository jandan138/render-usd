
import omni
import math
import numpy as np
from pxr import Usd
import json
from typing import Dict
from scipy.spatial.transform import Rotation as R
import omni.isaac.core.utils.numpy.rotations as rot_utils         # type: ignore
from omni.isaac.sensor import Camera                              # type: ignore
from omni.isaac.core import World                                 # type: ignore
from omni.isaac.core.prims import XFormPrim                       # type: ignore
from omni.isaac.core.utils.semantics import add_update_semantics  # type: ignore
from ..usd_utils.stage_utils import get_all_mesh_prims, get_all_mesh_prims_from_scope


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

def setup_instance_scene(stage: Usd.Stage) -> None:
    object_mesh_prims = get_all_mesh_prims(stage, world_node_path="/World/scene")
    for idx, prim in enumerate(object_mesh_prims):
        add_update_semantics(prim, semantic_label=f"instance_{idx}", type_label="class")
        print(f"[GRGenerator: Setup Instance Scene] Prim {prim.GetName()} is setted with semantic label 'instance_{idx}'.")
    
def setup_instance_copy_scene(stage: Usd.Stage) -> None:
    object_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Instances")
    structure_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure")
    all_mesh_prims = object_mesh_prims + structure_mesh_prims
    for idx, prim in enumerate(all_mesh_prims):
        add_update_semantics(prim, semantic_label=f"instance_{idx}", type_label="class")
        print(f"[GRGenerator: Setup Instance Scene] Prim {prim.GetName()} is setted with semantic label 'instance_{idx}'.")

def setup_semantic_object_copy_scene(stage: Usd.Stage, category_annotation: Dict[str, str]) -> None:
    object_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Instances")
    for prim in object_mesh_prims:
        prim_name = prim.GetName()
        semantic_label = category_annotation[prim_name]
        add_update_semantics(prim, semantic_label=semantic_label, type_label="class")
        print(f"[GRGenerator: Setup Semantic Scene] Prim {prim.GetName()} is setted with semantic label '{semantic_label}'.")

def setup_semantic_scene_copy(stage: Usd.Stage, object_annotation: Dict[str, str]) -> None:
    object_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Instances")
    wall_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure/Wall")
    floor_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure/Floor")
    ceiling_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure/Ceiling")
    background_mesh_prims = get_all_mesh_prims_from_scope(stage, scope_name="scene/Structure/BgWall")
    print(f"[DEBUG] object_mesh_prims length: {len(object_mesh_prims)}")
    print(f"[DEBUG] wall_mesh_prims length: {len(wall_mesh_prims)}")
    print(f"[DEBUG] floor_mesh_prims length: {len(floor_mesh_prims)}")
    print(f"[DEBUG] ceiling_mesh_prims length: {len(ceiling_mesh_prims)}")
    print(f"[DEBUG] background_mesh_prims length: {len(background_mesh_prims)}")
    for prim in object_mesh_prims:
        prim_name = prim.GetName()
        semantic_label = object_annotation[prim_name]
        add_update_semantics(prim, semantic_label=semantic_label, type_label="class")
        print(f"[GRGenerator: Setup Semantic Scene] Prim {prim_name} is setted with semantic label '{semantic_label}'.")
    for wall_prim in wall_mesh_prims:
        add_update_semantics(wall_prim, semantic_label="wall", type_label="class")
    for floor_prim in floor_mesh_prims:
        add_update_semantics(floor_prim, semantic_label="floor", type_label="class")
    for ceiling_prim in ceiling_mesh_prims:
        add_update_semantics(ceiling_prim, semantic_label="ceiling", type_label="class")
    for background_prim in background_mesh_prims:
        add_update_semantics(background_prim, semantic_label="background", type_label="class")


#==============================================================================
#                                INIT/SETUP CAMERA
#==============================================================================

def init_camera(
    camera_name: str = "camera",
    image_width: int = 640,
    image_height: int = 480,
    position: np.ndarray = np.array([0.0, 0.0, 0.0]),
    orientation: np.ndarray = np.array([0.0, 0.0, 0.0, 1.0]),
) -> Camera:
    camera = Camera(
        prim_path=f"/World/{camera_name}",
        resolution=(image_width, image_height),
        position=position,
        orientation=orientation
    )
    return camera

def set_camera_look_at(
    camera: Camera,
    target: XFormPrim | np.ndarray,
    distance: float = 0.4,
    elevation: float = 90.0,
    azimuth: float = 0.0,
) -> None:
    if isinstance(target, XFormPrim):
        # print("[DEBUG]: target is XFormPrim")
        target_position, _ = target.get_world_pose()
    else:
        target_position = target
    # print("target_position: ", target_position)
    elev_rad = math.radians(elevation)
    azim_rad = math.radians(azimuth)
    offset_x = distance * math.cos(elev_rad) * math.cos(azim_rad)
    offset_y = distance * math.cos(elev_rad) * math.sin(azim_rad)
    offset_z = distance * math.sin(elev_rad)
    camera_position = target_position + np.array([offset_x, offset_y, offset_z])
    rot = R.from_euler("xyz", [0, elevation, azimuth - 180], degrees=True)
    quaternion = rot.as_quat()
    quaternion = np.array([quaternion[3], quaternion[0], quaternion[1], quaternion[2]])
    # print("target_position: ", target_position)
    # print("camera_position: ", camera_position)
    # print("quaternion: ", quaternion)
    camera.set_world_pose(position=camera_position, orientation=quaternion)


def setup_camera(
    camera: Camera,
    focal_length: float = 18.0,
    clipping_range_min: float = 0.01,
    clipping_range_max: float = 1000000.0,
    vertical_aperture: float = 15.2908,
    horizontal_aperture: float = 20.0955,
    with_distance: bool = True,
    with_semantic: bool = False,
    with_bbox2d: bool = False,
    with_bbox3d: bool = False,
    with_motion_vector: bool = False,
    camera_params: dict | None = None,
    panorama: bool = False,
) -> None:
    camera.initialize()
    camera.set_focal_length(focal_length)
    camera.set_clipping_range(clipping_range_min, clipping_range_max)
    camera.set_vertical_aperture(vertical_aperture)
    camera.set_horizontal_aperture(horizontal_aperture)
    if with_distance:
        camera.add_distance_to_image_plane_to_frame()
    if with_semantic:
        camera.add_semantic_segmentation_to_frame()
    if with_bbox2d:
        camera.add_bounding_box_2d_tight_to_frame()
        camera.add_bounding_box_2d_loose_to_frame()
    if with_bbox3d:
        camera.add_bounding_box_3d_to_frame()
    if with_motion_vector:
        camera.add_motion_vectors_to_frame()
    if camera_params is not None:
        set_camera_rational_polynomial(camera, *camera_params)
    if panorama:
        camera.set_projection_type("fisheyeSpherical")

#==============================================================================
#                            PARSE CAMERA INFO
#==============================================================================

def get_depth(camera: Camera) -> np.ndarray | None:
    depth = camera._custom_annotators["distance_to_image_plane"].get_data()
    if isinstance(depth, np.ndarray) and depth.size > 0:
        return depth
    else:
        return None

def get_pointcloud(camera: Camera) -> np.ndarray | None:
    cloud = camera._custom_annotators["pointcloud"].get_data()["data"]
    if isinstance(cloud, np.ndarray) and cloud.size > 0:
        return cloud
    else:
        return None

def get_objectmask(camera: Camera) -> dict | None:
    annotator = camera._custom_annotators["semantic_segmentation"]
    annotation_data = annotator.get_data()
    mask = annotation_data["data"]
    idToLabels = annotation_data["info"]["idToLabels"]
    if isinstance(mask, np.ndarray) and mask.size > 0:
        return dict(mask=mask.astype(np.int8), id2labels=idToLabels)
    else:
        return None

def get_rgb(camera: Camera) -> np.ndarray | None:
    frame = camera.get_rgba()
    if isinstance(frame, np.ndarray) and frame.size > 0:
        frame = frame[:, :, :3]
        return frame
    else:
        return None

def get_bounding_box_2d_tight(camera: Camera) -> tuple[np.ndarray, dict]:
    annotator = camera._custom_annotators["bounding_box_2d_tight"]
    annotation_data = annotator.get_data()
    bbox = annotation_data["data"]
    info = annotation_data["info"]
    return bbox, info["idToLabels"]

def get_bounding_box_2d_loose(camera: Camera) -> tuple[np.ndarray, dict]:
    annotator = camera._custom_annotators["bounding_box_2d_loose"]
    annotation_data = annotator.get_data()
    bbox = annotation_data["data"]
    info = annotation_data["info"]
    return bbox, info["idToLabels"]

def get_bounding_box_3d(camera: Camera) -> tuple[list[dict], dict]:
    annotator = camera._custom_annotators["bounding_box_3d"]
    annotation_data = annotator.get_data()
    bbox = annotation_data["data"]
    info = annotation_data["info"]
    bbox_data = []
    for box in bbox:
        extents = {}
        (
            extents["class"],
            extents["x_min"],
            extents["y_min"],
            extents["z_min"],
            extents["x_max"],
            extents["y_max"],
            extents["z_max"],
            extents["transform"],
            _,
        ) = box
        extents["corners"] = get_world_corners_from_bbox3d(extents)
        bbox_data.append(extents)
    return bbox_data, info["idToLabels"]

def get_motion_vectors(camera: Camera) -> np.ndarray:
    annotator = camera._custom_annotators["motion_vectors"]
    annotation_data = annotator.get_data()
    motion_vectors = annotation_data
    return motion_vectors

def get_src(camera: Camera, type: str) -> np.ndarray | dict | None:
    if type == "rgb":
        return get_rgb(camera)
    if type == "depth":
        return get_depth(camera)
    if type == "cloud":
        return get_pointcloud(camera)
    if type == "seg":
        return get_objectmask(camera)
    if type == "bbox2d_tight":
        return get_bounding_box_2d_tight(camera)
    if type == "bbox2d_loose":
        return get_bounding_box_2d_loose(camera)
    if type == "bbox3d":
        return get_bounding_box_3d(camera)
    if type == "motion_vectors":
        return get_motion_vectors(camera)

def set_camera_rational_polynomial(
    camera: Camera,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    width: int,
    height: int,
    pixel_size: float = 3,
    f_stop: float = 2.0,
    focus_distance: float = 0.3,
    D: np.ndarray | None = None,
) -> Camera:
    if D is None:
        D = np.zeros(8)
    camera.initialize()
    camera.set_resolution([width, height])
    camera.set_clipping_range(0.02, 5)
    horizontal_aperture = pixel_size * 1e-3 * width
    vertical_aperture = pixel_size * 1e-3 * height
    focal_length_x = fx * pixel_size * 1e-3
    focal_length_y = fy * pixel_size * 1e-3
    focal_length = (focal_length_x + focal_length_y) / 2  # in mm
    camera.set_focal_length(focal_length / 10.0)
    camera.set_focus_distance(focus_distance)
    camera.set_lens_aperture(f_stop * 100.0)
    camera.set_horizontal_aperture(horizontal_aperture / 10.0)
    camera.set_vertical_aperture(vertical_aperture / 10.0)
    camera.set_clipping_range(0.05, 1.0e5)
    diagonal = 2 * math.sqrt(max(cx, width - cx) ** 2 + max(cy, height - cy) ** 2)
    diagonal_fov = 2 * math.atan2(diagonal, fx + fy) * 180 / math.pi
    camera.set_projection_type("fisheyePolynomial")
    camera.set_rational_polynomial_properties(width, height, cx, cy, diagonal_fov, D)
    return camera
