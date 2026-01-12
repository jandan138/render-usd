import os
import cv2
import pickle
import numpy as np

from tqdm import tqdm
from natsort import natsorted
from typing import List, Tuple, Dict, Union
from .images_utils import colorize_instance_mask_with_idlist, encode_mask_to_coco_format_rle, decode_RLE

# =====================================================================================
#                                   READ UTILS
# =====================================================================================
def get_instance_id(pkl_path: str):
    with open(pkl_path, "rb") as f:
        seg = pickle.load(f)
    return seg["id2labels"]

def get_instance_mask(pkl_path: str):
    with open(pkl_path, "rb") as f:
        seg = pickle.load(f)
    return seg["mask"]

# =====================================================================================
#                        VIDEO ANALYSIS UTILS
# =====================================================================================
def count_instance_occurrence_times_in_all_frames(instance_id_dir: str):
    """
    Count the number of times each instance appears across all frames.
    
    Args:
        instance_id_dir: Directory containing instance pickle files
        
    Returns:
        dict: A dictionary mapping instance names to their occurrence times (number of times)
    """
    statistics = {}
    instance_pkl_list = natsorted(os.listdir(instance_id_dir))
    for instance_pkl in tqdm(instance_pkl_list, desc="Counting instance appearances in all frames"):
        instanc_map_path = os.path.join(instance_id_dir, instance_pkl)
        instance_id = get_instance_id(instanc_map_path)    # Dict
        for _, instance_info in instance_id.items():
            instance_name = instance_info["class"]
            if instance_name not in statistics.keys():
                statistics[instance_name] = 0
            statistics[instance_name] += 1
    sorted_statistics = dict(sorted(statistics.items(), key=lambda x: x[1], reverse=True))
    return sorted_statistics

def get_instance_continuity_frames(instance_id_dir: str):
    """
    Get the continuity frames of each instance.
    
    Args:
        instance_id_dir: Directory containing instance pickle files
        
    Returns:
        dict: A dictionary mapping instance names to lists of continuity frames
    """
    statistics = {}
    instance_all_frame_indices = get_instance_frame_indices(instance_id_dir)
    for instance_name, frame_indices in instance_all_frame_indices.items():
        continuity_frames = check_continuity(frame_indices)
        statistics[instance_name] = continuity_frames
    return statistics

def get_instance_frame_indices(instance_id_dir: str):
    """
    Get the frame indices where each instance appears.
    
    Args:
        instance_id_dir: Directory containing instance pickle files
        
    Returns:
        dict: A dictionary mapping instance names to lists of frame indices where they appear
    """
    statistics = {}
    instance_pkl_list = natsorted(os.listdir(instance_id_dir))
    for instance_pkl in tqdm(instance_pkl_list, desc="Tracking instance per frame"):
        instanc_map_path = os.path.join(instance_id_dir, instance_pkl)
        instance_id = get_instance_id(instanc_map_path)    # Dict
        for _, instance_info in instance_id.items():
            instance_name = instance_info["class"]
            if instance_name not in statistics.keys():
                statistics[instance_name] = []
            statistics[instance_name].append(instance_pkl.split("_")[0])
    return statistics

def get_frame_instance_number(instance_id_dir: str):
    """
    Get the number of instances in each frame.
    
    Args:
        instance_id_dir: Directory containing instance pickle files
        
    Returns:
        dict: A dictionary mapping frame indices to the number of instances in that frame
    """
    statistics = {}
    instance_pkl_list = natsorted(os.listdir(instance_id_dir))
    for instance_pkl in tqdm(instance_pkl_list, desc="Counting instances per frame"):
        frame_index = instance_pkl.split("_")[0]
        instanc_map_path = os.path.join(instance_id_dir, instance_pkl)
        instance_id = get_instance_id(instanc_map_path)
        statistics[frame_index] = len(instance_id) - 2  # -2 for background and unknown
    return statistics

# =====================================================================================
#                        VISUALIZATION UTILS
# =====================================================================================
def visualize_frames_with_less_instances(instance_dir: str, save_dir: str):
    os.makedirs(save_dir, exist_ok=True)
    rgb_dir = instance_dir.replace("instance", "rgb")
    instance_list = natsorted(os.listdir(instance_dir))
    for instance in tqdm(instance_list, desc="Visualizing frames with less instances"):
        frame_index = instance.split("_")[0]
        instanc_map_path = os.path.join(instance_dir, instance)
        instance_id = get_instance_id(instanc_map_path)
        instance_number = len(instance_id) - 2    # -2 for background and unknown
        if instance_number < 4:
            instance_mask = get_instance_mask(instanc_map_path)
            colorized_instance_mask = colorize_instance_mask_with_idlist(instance_mask)
            rgb_image = cv2.imread(os.path.join(rgb_dir, f"{frame_index}.jpg"))
            # print(f"[DEBUG] rgb_image.shape: {rgb_image.shape}")
            # print(f"[DEBUG] colorized_instance_mask.shape: {colorized_instance_mask.shape}")
            combined_image = np.hstack([rgb_image, colorized_instance_mask])
            cv2.imwrite(os.path.join(save_dir, f"frame_{frame_index}_with_{instance_number}_instances.jpg"), combined_image)

def visualize_RLE_with_RGB(instance_mask, instance_id, rgb_image, save_path):
    rle_encoding = encode_mask_to_coco_format_rle(instance_mask, instance_id)
    mask = decode_RLE(rle_encoding)
    
    mask_uint8 = (mask * 255).astype(np.uint8)
    mask_rgb = cv2.cvtColor(mask_uint8, cv2.COLOR_GRAY2BGR)
    
    combined_image = np.hstack([rgb_image, mask_rgb])
    cv2.imwrite(save_path, combined_image)

# =====================================================================================
#                        COMPUTATIONAL UTILS
# =====================================================================================
def get_continuity_info(num_list: List[int]) -> Dict:
    """
    Analyze the continuity of a list of numbers.
    
    Args:
        num_list: List of integers to analyze
        
    Returns:
        Dictionary containing continuity information including segments and gaps
    """
    if not num_list:
        return {
            "is_continuous": True,
            "num_segments": 0,
            "segments": [],
            "gaps": []
        }
    
    nums = sorted(set(int(x) for x in num_list))
    segments = []
    gaps = []
    
    segment_start = nums[0]
    for i in range(1, len(nums)):
        if nums[i] != nums[i-1] + 1:
            segments.append((segment_start, nums[i-1]))
            gaps.append((nums[i-1], nums[i]))
            segment_start = nums[i]
    segments.append((segment_start, nums[-1]))
    
    return {
        "is_continuous": len(segments) == 1,
        "num_segments": len(segments),
        "segments": segments,
        "gaps": gaps,
        "gaps_number": [gap[1] - gap[0] for gap in gaps]
    }

def check_instance_mask(instance_id_dir: str):
    instance_pkl_list = natsorted(os.listdir(instance_id_dir))
    for instance_pkl in tqdm(instance_pkl_list, desc="Checking instance mask"):
        instanc_map_path = os.path.join(instance_id_dir, instance_pkl)
        instance_mask = get_instance_mask(instanc_map_path)

        labels = np.unique(instance_mask)
        if 1 in labels or 0 in labels:
            # print(f"[DEBUG] {instance_pkl}: {labels}")
            zero_count = np.sum(instance_mask == 0)
            # print(f"[DEBUG] {instance_pkl}: Number of zeros in mask = {zero_count}")

def create_masks_from_segments(frame_ids: List[int], instance_id_dir: str, instance_id: int):
    masks = {}
    for frame_id in frame_ids:
        # Convert numpy int64 to Python int for JSON serialization
        frame_id_int = int(frame_id)
        instance_pkl_path = os.path.join(instance_id_dir, f"{frame_id_int}_seg.pkl")
        instance_mask = get_instance_mask(instance_pkl_path)
        masks[frame_id_int] = encode_mask_to_coco_format_rle(instance_mask, instance_id)
    return [masks]

def get_instance_id_and_name_dict(instance_id_dir: str):
    instance_id_and_name_dict = {}
    instance_pkl_list = natsorted(os.listdir(instance_id_dir))
    for instance_pkl in tqdm(instance_pkl_list, desc="Getting instance ID and name dictionary"):
        instance_pkl_path = os.path.join(instance_id_dir, instance_pkl)
        instance_ids = get_instance_id(instance_pkl_path)
        for instance_id, instance_info in instance_ids.items():
            instance_name = instance_info["class"]
            if instance_name == "BACKGROUND" or instance_name == "UNLABELLED":
                # print(f"[DEBUG] {instance_pkl}: {instance_name}")
                continue
            instance_id_and_name_dict[instance_name] = instance_id
    # sort by instance id
    instance_id_and_name_dict = dict(natsorted(instance_id_and_name_dict.items(), key=lambda x: x[1]))
    return instance_id_and_name_dict

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance_id", type=int, default=65)
    parser.add_argument("--frame_index", type=int, default=100)
    args = parser.parse_args()
    
    instance_dir = "/cpfs/user/caopeizhou/projects/GRGenerator/output/camera_poses/GRScenes/part1/101_usd/0001/exploration/rendered_custom/trajectory_0_0_0/instance"
    rgb_dir = "/cpfs/user/caopeizhou/projects/GRGenerator/output/camera_poses/GRScenes/part1/101_usd/0001/exploration/rendered_custom/trajectory_0_0_0/rgb"
    frame_index = args.frame_index
    instance_id = args.instance_id
    pkl_path = os.path.join(instance_dir, f"{frame_index}_seg.pkl")
    rgb_path = os.path.join(rgb_dir, f"{frame_index}.jpg")
    instance_ids = get_instance_id(pkl_path)
    print(instance_ids)
    instance_mask = get_instance_mask(pkl_path)
    rgb_image = cv2.imread(rgb_path)
    visualize_RLE_with_RGB(instance_mask, instance_id, rgb_image, f"./_test/_debug_rle/mask_{frame_index}.png")

    # instance_continuity_frames = get_instance_continuity_frames(instance_dir)
    # for instance_name, continuity_frames in instance_continuity_frames.items():
    #     print(f"[DEBUG] {instance_name}: {continuity_frames}")




