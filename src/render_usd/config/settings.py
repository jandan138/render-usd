import os
from pathlib import Path

# Determine project root relative to this file
# config -> render_usd -> src -> root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Asset paths
ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_MDL_PATH = ASSETS_DIR / "materials" / "default.mdl"
DEFAULT_ENVIRONMENT_PATH = ASSETS_DIR / "environments" / "background.usd"

# Default MDL search paths for GRScenes material resolution
# These directories contain MI_*.mdl files and KooPbr modules needed by GRScenes USD assets
DEFAULT_MDL_SEARCH_PATHS = [
    "/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/Material/mdl",
    "/cpfs/shared/simulation/liyangzi/grutopia/assets/scenes/GRScenes-100/home_scenes/Materials",
]

# Default Data Paths (Can be overridden via arguments)
DEFAULT_GRSCENES_DIR = Path("/cpfs/user/caopeizhou/data/GRScenes/instances")
DEFAULT_GRSCENES_SCENE_DIR = Path("/cpfs/user/caopeizhou/projects/GRGenerator/_scenes/GRScenes")
DEFAULT_GRSCENES100_ASSETS_DIR = Path("/cpfs/user/caopeizhou/data/GRScenes-100/Asset_Library_all")
DEFAULT_GRSCENES100_SAVE_DIR = Path("/oss-caopeizhou/data/GRScenes-100/all_assets_renderings")

# Simulation Config
SIM_CONFIG = {
    "headless": True,
    "anti_aliasing": 4,
    "multi_gpu": False,
    "renderer": "PathTracing"
}
