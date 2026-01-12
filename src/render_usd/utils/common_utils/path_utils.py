import os, sys, inspect
from pathlib import Path
from typing import List, Dict, Optional, Union
from natsort import natsorted

class DataPathParser:
    DEFAULT_ROOT = Path('/oss-caopeizhou/data/GRGenerator/exploration')

    def __init__(
        self, 
        part: int, 
        usd: int, 
        scene: str,
        root_dir : Union[str, Path] = None
    ):
        self.part = part
        self.usd = usd
        self.scene = scene
        if root_dir is None:
            root_dir = self.DEFAULT_ROOT
        self.root_dir = Path(root_dir) if isinstance(root_dir, str) else root_dir

    def get_part_dir(self) -> Path:
        return self.root_dir / f"part{self.part}"

    def get_usd_list(self, start_idx: int = None, end_idx: int = None) -> List[str]:
        part_dir = self.get_part_dir()
        if self.usd:
            usd_list = [f"{self.usd}_usd"]
        else:
            usd_list = natsorted([usd for usd in os.listdir(part_dir) if usd != "121_usd"])[start_idx:end_idx]
        return usd_list

    def get_scene_list_in_usd_folder(self, usd_index: str) -> List[str]:
        usd_dir = self.get_part_dir() / usd_index
        if self.scene:
            scene_list = [self.scene]
        else:
            scene_list = natsorted(os.listdir(usd_dir))
        return scene_list

    def get_scene_lists(self) -> List[List[str]]:
        usd_list = self.get_usd_list()
        scene_lists = [self.get_scene_list_in_usd_folder(usd) for usd in usd_list]
        return scene_lists

# ----------------------------------------------------------------------------------
#                            SYSTEM PATH UTILS
# ----------------------------------------------------------------------------------

def add_path_to_sys_path(path, mode, frame):
    assert mode == "unchanged" or mode == "relative_to_cwd" or mode == "relative_to_current_source_dir"
    if mode == "unchanged":
        if path not in sys.path:
            sys.path.insert(0,path)
    if mode == "relative_to_cwd":
        realpath = os.path.realpath(os.path.abspath(path))
        if realpath not in sys.path:
            sys.path.insert(0,realpath)
    if mode == "relative_to_current_source_dir":
        realpath = os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(inspect.getfile(frame)),path)))
        if realpath not in sys.path:
            sys.path.insert(0,realpath)

def get_current_source_file_path(frame):
    return os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(inspect.getfile(frame)))))

# ----------------------------------------------------------------------------------
#                           FOLDER PATH UTILS
# ----------------------------------------------------------------------------------

# Find file path in specific suffix
def find_file_in_folder(dir, suffix):
    file_names = os.listdir(dir)
    for file_name in file_names:
        if file_name.endswith(suffix):
            target_path = os.path.join(dir, file_name)
            return target_path
    return None  

# Find all file paths in specific suffix
def find_all_files_in_folder(dir, suffix):
    file_names = os.listdir(dir)
    target_paths = []
    for file_name in file_names:
        if file_name.endswith(suffix):
            target_path = os.path.join(dir, file_name)
            target_paths.append(target_path)
    return target_paths



    
