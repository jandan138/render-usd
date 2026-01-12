import omni
import math
import numpy as np
from scipy.spatial.transform import Rotation as R
from omni.isaac.sensor import Camera
from omni.isaac.core.prims import XFormPrim
from typing import Tuple, List, Dict, Optional, Union

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
    target: Union[XFormPrim, np.ndarray],
    distance: float = 0.4,
    elevation: float = 90.0,
    azimuth: float = 0.0,
) -> None:
    if isinstance(target, XFormPrim):
        target_position, _ = target.get_world_pose()
    else:
        target_position = target
    
    elev_rad = math.radians(elevation)
    azim_rad = math.radians(azimuth)
    offset_x = distance * math.cos(elev_rad) * math.cos(azim_rad)
    offset_y = distance * math.cos(elev_rad) * math.sin(azim_rad)
    offset_z = distance * math.sin(elev_rad)
    camera_position = target_position + np.array([offset_x, offset_y, offset_z])
    rot = R.from_euler("xyz", [0, elevation, azimuth - 180], degrees=True)
    quaternion = rot.as_quat()
    quaternion = np.array([quaternion[3], quaternion[0], quaternion[1], quaternion[2]])
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
    camera_params: Optional[dict] = None,
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
        set_camera_rational_polynomial(camera, **camera_params)
    if panorama:
        camera.set_projection_type("fisheyeSpherical")

#==============================================================================
#                            PARSE CAMERA INFO
#==============================================================================

def get_depth(camera: Camera) -> Optional[np.ndarray]:
    depth = camera._custom_annotators["distance_to_image_plane"].get_data()
    if isinstance(depth, np.ndarray) and depth.size > 0:
        return depth
    else:
        return None

def get_pointcloud(camera: Camera) -> Optional[np.ndarray]:
    cloud = camera._custom_annotators["pointcloud"].get_data()["data"]
    if isinstance(cloud, np.ndarray) and cloud.size > 0:
        return cloud
    else:
        return None

def get_objectmask(camera: Camera) -> Optional[dict]:
    annotator = camera._custom_annotators["semantic_segmentation"]
    annotation_data = annotator.get_data()
    mask = annotation_data["data"]
    idToLabels = annotation_data["info"]["idToLabels"]
    if isinstance(mask, np.ndarray) and mask.size > 0:
        return dict(mask=mask.astype(np.int8), id2labels=idToLabels)
    else:
        return None

def get_rgb(camera: Camera) -> Optional[np.ndarray]:
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
    # Note: get_world_corners_from_bbox3d was missing in original code.
    # We keep the structure but it will fail if called.
    # from render_usd.utils.common_utils.sim_utils import get_world_corners_from_bbox3d
    
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
        # extents["corners"] = get_world_corners_from_bbox3d(extents) # Commented out due to missing definition
        bbox_data.append(extents)
    return bbox_data, info["idToLabels"]

def get_motion_vectors(camera: Camera) -> np.ndarray:
    annotator = camera._custom_annotators["motion_vectors"]
    annotation_data = annotator.get_data()
    motion_vectors = annotation_data
    return motion_vectors

def get_src(camera: Camera, type: str) -> Union[np.ndarray, dict, None]:
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
    return None

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
    D: Optional[np.ndarray] = None,
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
