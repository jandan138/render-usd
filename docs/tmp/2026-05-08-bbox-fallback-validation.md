# Bbox Fallback Validation

## Problem

Validate that the mesh-point bbox fallback corrects oversized authored extents on the two known bad GRScenes assets while leaving one sampled normal control asset unchanged.

## Investigation

I ran a read-only Python diagnostic from the `bbox-fallback` worktree. For each known asset, the script opened the USD stage, selected the default prim when present and valid, otherwise selected the pseudo-root, then compared:

- old bbox: `compute_bbox(prim, use_mesh_point_fallback=False)`
- new bbox: `compute_bbox(prim)`
- old/new diagonal lengths
- whether the fallback changed the bbox
- old/new min/max values

Command, run from `/cpfs/shared/simulation/zhuzihou/dev/render-usd/.worktrees/bbox-fallback` with the available system Python environment:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python - <<'PY'
import numpy as np
from pxr import Usd
from render_usd.utils.usd_utils.prim_utils import compute_bbox

assets = {
    "tiny_basket": "/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/basket/040600389fdab577a5376c28e6c5eb15/usd/040600389fdab577a5376c28e6c5eb15.usd",
    "blank_basket": "/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/basket/6ae01f7e1ba19fc58a6f9d0b1102c3d1/usd/6ae01f7e1ba19fc58a6f9d0b1102c3d1.usd",
    "normal_backpack": "/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/backpack/7e66385cf06355dd76b9340ec9bdfaee/usd/7e66385cf06355dd76b9340ec9bdfaee.usd",
}

for name, path in assets.items():
    stage = Usd.Stage.Open(path)
    if stage is None:
        raise RuntimeError(f"failed to open {name}: {path}")
    default_prim = stage.GetDefaultPrim()
    prim = default_prim if default_prim and default_prim.IsValid() else stage.GetPseudoRoot()
    old_bbox = compute_bbox(prim, use_mesh_point_fallback=False)
    new_bbox = compute_bbox(prim)
    old_diag = float(np.linalg.norm(old_bbox[1] - old_bbox[0]))
    new_diag = float(np.linalg.norm(new_bbox[1] - new_bbox[0]))
    changed = not np.allclose(old_bbox, new_bbox)
    print(f"asset={name}")
    print(f"path={path}")
    print(f"prim={prim.GetPath()}")
    print(f"old_diag={old_diag:.6f}")
    print(f"new_diag={new_diag:.6f}")
    print(f"fallback_changed={changed}")
    print(f"old_min={old_bbox[0].tolist()}")
    print(f"old_max={old_bbox[1].tolist()}")
    print(f"new_min={new_bbox[0].tolist()}")
    print(f"new_max={new_bbox[1].tolist()}")
    print()
PY
```

Output:

```text
asset=tiny_basket
path=/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/basket/040600389fdab577a5376c28e6c5eb15/usd/040600389fdab577a5376c28e6c5eb15.usd
prim=/Root
old_diag=636.184620
new_diag=62.323327
fallback_changed=True
old_min=[-229.40699768066426, -184.39599609375017, -116.89199829101562]
old_max=[229.77499389648457, 177.8500061035158, 133.4290008544922]
new_min=[-16.8185386657715, -12.572849273681651, -23.024106979370117]
new_max=[16.8185386657715, 12.572849273681651, 23.024106979370117]

asset=blank_basket
path=/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/basket/6ae01f7e1ba19fc58a6f9d0b1102c3d1/usd/6ae01f7e1ba19fc58a6f9d0b1102c3d1.usd
prim=/Root
old_diag=4239.049048
new_diag=42.769519
fallback_changed=True
old_min=[-1648.5376312400138, -888.6254858036373, 15.099280514115899]
old_max=[1648.5376312400138, 888.6183542249995, 2000.1020196968252]
new_min=[-15.600019796568489, -11.109125575657844, -9.514969748398686]
new_max=[15.600019796568489, 11.109125575657844, 9.514969748398686]

asset=normal_backpack
path=/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/backpack/7e66385cf06355dd76b9340ec9bdfaee/usd/7e66385cf06355dd76b9340ec9bdfaee.usd
prim=/Root
old_diag=76.540939
new_diag=76.540939
fallback_changed=False
old_min=[-20.522300720214844, 10.233200073242188, -29.428799438476563]
old_max=[13.045799255371094, 45.83489990234375, 29.428799438476563]
new_min=[-20.522300720214844, 10.233200073242188, -29.428799438476563]
new_max=[13.045799255371094, 45.83489990234375, 29.428799438476563]
```

## Solution

Task 3 did not modify production code or tests. The validation confirms that, for these three sampled assets, the default `compute_bbox(prim)` path uses the mesh-point fallback only when authored extents are much larger than mesh-point-derived bounds.

## Results

- `tiny_basket`: old diagonal `636.184620`, new diagonal `62.323327`, fallback changed bbox: `True`.
- `blank_basket`: old diagonal `4239.049048`, new diagonal `42.769519`, fallback changed bbox: `True`.
- `normal_backpack`: old/new diagonal `76.540939`, fallback changed bbox: `False`.

The results match the expected high-level behavior for all three sampled real assets.

## Render Smoke Test

I also rendered the `tiny_basket` sample into a temporary output directory using Isaac Sim from the shared conda environment.

Command:

```bash
source "/cpfs/shared/simulation/zhuzihou/dev/render-usd/miniconda/bin/activate" render-usd && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && export OMNI_KIT_ACCEPT_EULA=YES && python -m render_usd.cli single --usd_path "/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/basket/040600389fdab577a5376c28e6c5eb15/usd/040600389fdab577a5376c28e6c5eb15.usd" --output_dir "docs/tmp/bbox-fallback-render-validation" --naming_style view --overwrite
```

Result:

- Command completed and wrote `front.png`, `left.png`, `back.png`, and `right.png` under `docs/tmp/bbox-fallback-render-validation/040600389fdab577a5376c28e6c5eb15/`.
- Isaac Sim emitted expected headless/windowing warnings and camera annotator `distance_to_image_plane` warnings, but the render loop completed for `1/1` objects.

Rendered image visibility metrics, computed against the dark-gray `(40, 40, 40)` background:

```text
back.png: fg_ratio=0.310036 bbox=286x404 bbox_area_ratio=0.440765
front.png: fg_ratio=0.305561 bbox=277x393 bbox_area_ratio=0.415272
left.png: fg_ratio=0.287891 bbox=257x364 bbox_area_ratio=0.356857
right.png: fg_ratio=0.350117 bbox=359x355 bbox_area_ratio=0.486164
```

These metrics are far above the previous tiny-screening threshold (`bbox_area_ratio <= 0.02` and max dimension `<= 80`), so the smoke-rendered tiny basket is visibly framed after the bbox fallback.

## Risks / Next Step

This validation covers three representative real assets only. A broader batch over additional categories would reduce the risk of false positives where authored extents are intentionally larger than mesh points.
