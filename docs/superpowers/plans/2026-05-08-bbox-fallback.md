# Fallback Geometry BBox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conservative fallback geometry bbox so camera placement ignores clearly inflated authored USD extents.

**Architecture:** Keep the public renderer call as `compute_bbox(prim)`. Extract the existing `ComputeWorldBound()` behavior, add a private recursive fallback geometry helper, and choose that fallback bbox only when the authored bbox diagonal is at least `5.0x` larger. Meshes contribute transformed points; visible default-purpose non-mesh `UsdGeom.Boundable` prims contribute their USD world bounds. Tests create in-memory USD stages and do not require Isaac Sim.

**Tech Stack:** Python, NumPy, pxr.Usd, pxr.UsdGeom, pytest

---

## File Structure

- Modify: `src/render_usd/utils/usd_utils/prim_utils.py`
  - Add `_compute_authored_world_bbox()` for the current bbox behavior.
  - Add `_compute_mesh_point_bbox()` for fallback geometry union bounds. Meshes use transformed points; visible default-purpose non-mesh `UsdGeom.Boundable` prims contribute their authored world bounds.
  - Add `_is_valid_fallback_bbox()` to reject non-finite or zero-diagonal fallback bounds.
  - Extend `compute_bbox()` with optional fallback parameters while preserving existing call sites.
- Create: `tests/test_prim_utils_bbox.py`
  - Test in-memory USD stages for normal extents, inflated extents, transforms, invalid points, and disabled fallback.
- Create: `docs/tmp/2026-05-08-bbox-fallback-validation.md`
  - Record commands, results, real-asset bbox diagnostics, and remaining risk.

## Task 1: Add Failing Unit Tests

**Files:**
- Create: `tests/test_prim_utils_bbox.py`

- [ ] **Step 1.1: Create tests for authored-vs-mesh bbox selection**

Create `tests/test_prim_utils_bbox.py` with this content:

```python
import math
from pathlib import Path

import numpy as np
import pytest
from pxr import Gf, Usd, UsdGeom

from render_usd.utils.usd_utils.prim_utils import compute_bbox


def _root_with_mesh(points, extent, translate=None):
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    mesh = UsdGeom.Mesh.Define(stage, "/Root/Mesh")
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr([3])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2])
    mesh.CreateExtentAttr(extent)
    if translate is not None:
        UsdGeom.Xformable(mesh.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(*translate))
    return root.GetPrim()


def _diag(bbox):
    bbox = np.asarray(bbox, dtype=float)
    return float(np.linalg.norm(bbox[1] - bbox[0]))


def test_compute_bbox_keeps_authored_bbox_when_ratio_below_threshold():
    prim = _root_with_mesh(
        points=[Gf.Vec3f(0, 0, 0), Gf.Vec3f(1, 0, 0), Gf.Vec3f(0, 1, 0)],
        extent=[Gf.Vec3f(0, 0, 0), Gf.Vec3f(2, 2, 0)],
    )

    bbox = compute_bbox(prim, extent_fallback_ratio=5.0)

    np.testing.assert_allclose(bbox, np.array([[0, 0, 0], [2, 2, 0]], dtype=float))


def test_compute_bbox_uses_mesh_points_when_authored_bbox_is_inflated():
    prim = _root_with_mesh(
        points=[Gf.Vec3f(0, 0, 0), Gf.Vec3f(1, 0, 0), Gf.Vec3f(0, 1, 0)],
        extent=[Gf.Vec3f(-100, -100, -100), Gf.Vec3f(100, 100, 100)],
    )

    bbox = compute_bbox(prim, extent_fallback_ratio=5.0)

    np.testing.assert_allclose(bbox, np.array([[0, 0, 0], [1, 1, 0]], dtype=float))
    assert _diag(bbox) < 2.0


def test_compute_bbox_applies_mesh_world_transform_before_fallback():
    prim = _root_with_mesh(
        points=[Gf.Vec3f(0, 0, 0), Gf.Vec3f(1, 0, 0), Gf.Vec3f(0, 2, 0)],
        extent=[Gf.Vec3f(-100, -100, -100), Gf.Vec3f(100, 100, 100)],
        translate=(10, 20, 30),
    )

    bbox = compute_bbox(prim, extent_fallback_ratio=5.0)

    np.testing.assert_allclose(bbox, np.array([[10, 20, 30], [11, 22, 30]], dtype=float))


def test_compute_bbox_can_disable_mesh_point_fallback():
    prim = _root_with_mesh(
        points=[Gf.Vec3f(0, 0, 0), Gf.Vec3f(1, 0, 0), Gf.Vec3f(0, 1, 0)],
        extent=[Gf.Vec3f(-100, -100, -100), Gf.Vec3f(100, 100, 100)],
    )

    bbox = compute_bbox(prim, use_mesh_point_fallback=False)

    np.testing.assert_allclose(bbox, np.array([[-100, -100, -100], [100, 100, 100]], dtype=float))


def test_compute_bbox_keeps_authored_bbox_when_mesh_points_are_missing():
    prim = _root_with_mesh(
        points=[],
        extent=[Gf.Vec3f(-3, -4, -5), Gf.Vec3f(3, 4, 5)],
    )

    bbox = compute_bbox(prim, extent_fallback_ratio=5.0)

    np.testing.assert_allclose(bbox, np.array([[-3, -4, -5], [3, 4, 5]], dtype=float))


def test_compute_bbox_ignores_invalid_mesh_points():
    prim = _root_with_mesh(
        points=[
            Gf.Vec3f(0, 0, 0),
            Gf.Vec3f(float("nan"), 0, 0),
            Gf.Vec3f(1, 1, 0),
        ],
        extent=[Gf.Vec3f(-100, -100, -100), Gf.Vec3f(100, 100, 100)],
    )

    bbox = compute_bbox(prim, extent_fallback_ratio=5.0)

    np.testing.assert_allclose(bbox, np.array([[0, 0, 0], [1, 1, 0]], dtype=float))
```

- [ ] **Step 1.2: Run tests and verify they fail before implementation**

Run:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q
```

Expected result before implementation: tests fail with `TypeError: compute_bbox() got an unexpected keyword argument` or assertion failures showing current authored bbox behavior.

## Task 2: Implement Fallback Geometry BBox

**Files:**
- Modify: `src/render_usd/utils/usd_utils/prim_utils.py`
- Test: `tests/test_prim_utils_bbox.py`

- [ ] **Step 2.1: Replace `compute_bbox()` with guarded fallback helpers**

Edit `src/render_usd/utils/usd_utils/prim_utils.py` so the compute section contains guarded fallback helpers equivalent to the final implementation:

```python
def _compute_authored_world_bbox(prim: Usd.Prim) -> np.ndarray:
    imageable: UsdGeom.Imageable = UsdGeom.Imageable(prim)
    time = Usd.TimeCode.Default()
    bound = imageable.ComputeWorldBound(time, UsdGeom.Tokens.default_)
    bound_range = bound.ComputeAlignedBox()
    return np.array([bound_range.min, bound_range.max])


def _is_default_visible_imageable(imageable: UsdGeom.Imageable, time: Usd.TimeCode) -> bool:
    if imageable.ComputeEffectiveVisibility(time=time) == UsdGeom.Tokens.invisible:
        return False
    return imageable.ComputePurpose() == UsdGeom.Tokens.default_


def _is_valid_fallback_bbox(bbox: np.ndarray | None) -> bool:
    if bbox is None or not np.isfinite(bbox).all():
        return False
    return np.linalg.norm(bbox[1] - bbox[0]) > 0


def _compute_single_mesh_point_bbox(prim: Usd.Prim) -> np.ndarray | None:
    time = Usd.TimeCode.Default()
    imageable: UsdGeom.Imageable = UsdGeom.Imageable(prim)
    if not _is_default_visible_imageable(imageable, time):
        return None

    points = prim.GetAttribute("points").Get()
    try:
        points = np.array(to_list(points), dtype=float)
        if points.size == 0:
            return None
        if points.ndim != 2 or points.shape[1] != 3:
            return None
    except (TypeError, ValueError):
        return None

    xform_world_transform = np.array(
        imageable.ComputeLocalToWorldTransform(time),
        dtype=float,
    )

    ones = np.ones((points.shape[0], 1))
    points_h = np.hstack([points, ones])
    points_transformed_h = np.dot(points_h, xform_world_transform)
    with np.errstate(divide="ignore", invalid="ignore"):
        points_transformed = (
            points_transformed_h[:, :3]
            / points_transformed_h[:, 3][:, np.newaxis]
        )
    valid_points_mask = np.isfinite(points_transformed).all(axis=1)
    points_transformed = points_transformed[valid_points_mask]
    if points_transformed.size == 0:
        return None
    return np.array(
        [np.min(points_transformed, axis=0), np.max(points_transformed, axis=0)]
    )


def _compute_boundable_bbox(prim: Usd.Prim) -> np.ndarray | None:
    time = Usd.TimeCode.Default()
    imageable: UsdGeom.Imageable = UsdGeom.Imageable(prim)
    if not _is_default_visible_imageable(imageable, time):
        return None

    boundable: UsdGeom.Boundable = UsdGeom.Boundable(prim)
    bound_range = boundable.ComputeWorldBound(time, UsdGeom.Tokens.default_).ComputeAlignedBox()
    bbox = np.array([bound_range.min, bound_range.max])
    if not _is_valid_fallback_bbox(bbox):
        return None
    return bbox


def _union_bbox(first: np.ndarray | None, second: np.ndarray | None) -> np.ndarray | None:
    if first is None:
        return second
    if second is None:
        return first
    return np.array(
        [
            np.minimum(first[0], second[0]),
            np.maximum(first[1], second[1]),
        ]
    )


def _compute_mesh_point_bbox(prim: Usd.Prim) -> np.ndarray | None:
    bbox = None

    if prim.IsA(UsdGeom.Mesh):
        bbox = _compute_single_mesh_point_bbox(prim)
    elif prim.IsA(UsdGeom.Boundable):
        bbox = _compute_boundable_bbox(prim)

    for child in prim.GetChildren():
        bbox = _union_bbox(bbox, _compute_mesh_point_bbox(child))

    if not _is_valid_fallback_bbox(bbox):
        return None
    return bbox


def compute_bbox(
    prim: Usd.Prim,
    use_mesh_point_fallback: bool = True,
    extent_fallback_ratio: float = 5.0,
) -> np.ndarray:
    """
    Compute a world-space bounding box for a prim.

    The default path preserves USD `ComputeWorldBound()` behavior. When authored
    extents are clearly inflated compared with fallback geometry, use the
    fallback bbox so camera placement frames the visible geometry.
    """
    if not np.isfinite(extent_fallback_ratio) or extent_fallback_ratio <= 0:
        raise ValueError("extent_fallback_ratio must be finite and positive")

    authored_bbox = _compute_authored_world_bbox(prim)
    if not use_mesh_point_fallback:
        return authored_bbox

    mesh_point_bbox = _compute_mesh_point_bbox(prim)
    if not _is_valid_fallback_bbox(mesh_point_bbox):
        return authored_bbox

    if not np.isfinite(authored_bbox).all():
        return mesh_point_bbox

    authored_diag = np.linalg.norm(authored_bbox[1] - authored_bbox[0])
    mesh_diag = np.linalg.norm(mesh_point_bbox[1] - mesh_point_bbox[0])
    if not np.isfinite(authored_diag) or not np.isfinite(mesh_diag) or mesh_diag <= 0:
        return authored_bbox

    if authored_diag / mesh_diag >= extent_fallback_ratio:
        return mesh_point_bbox

    return authored_bbox
```

- [ ] **Step 2.2: Run focused tests**

Run:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q
```

Expected result after implementation: all tests in `tests/test_prim_utils_bbox.py` pass.

- [ ] **Step 2.3: Run syntax check**

Run:

```bash
python -m compileall src/render_usd/utils/usd_utils/prim_utils.py
```

Expected result: command exits `0` and compiles the modified file.

## Task 3: Validate Real Asset BBox Behavior

**Files:**
- Modify: `docs/tmp/2026-05-08-bbox-fallback-validation.md`

- [ ] **Step 3.1: Run bbox diagnostics on known assets**

Run this command:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python - <<'PY'
from pathlib import Path
import numpy as np
from pxr import Usd

from render_usd.utils.usd_utils.prim_utils import compute_bbox

ASSETS = {
    "tiny_basket": "/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/basket/040600389fdab577a5376c28e6c5eb15/usd/040600389fdab577a5376c28e6c5eb15.usd",
    "blank_basket": "/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/basket/6ae01f7e1ba19fc58a6f9d0b1102c3d1/usd/6ae01f7e1ba19fc58a6f9d0b1102c3d1.usd",
    "normal_backpack": "/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/backpack/7e66385cf06355dd76b9340ec9bdfaee/usd/7e66385cf06355dd76b9340ec9bdfaee.usd",
}

def diag(bbox):
    return float(np.linalg.norm(bbox[1] - bbox[0]))

for name, path in ASSETS.items():
    stage = Usd.Stage.Open(path)
    default_prim = stage.GetDefaultPrim()
    prim = default_prim if default_prim and default_prim.IsValid() else stage.GetPseudoRoot()
    old_bbox = compute_bbox(prim, use_mesh_point_fallback=False)
    new_bbox = compute_bbox(prim)
    print(f"{name}: old_diag={diag(old_bbox):.6f} new_diag={diag(new_bbox):.6f} used_fallback={not np.allclose(old_bbox, new_bbox)}")
PY
```

Expected result:

```text
tiny_basket: old_diag near 636.184620, new_diag near 62.323327, used_fallback=True
blank_basket: old_diag near 4239.049048, new_diag near 42.769519, used_fallback=True
normal_backpack: old_diag near 76.540939, new_diag near 76.540939, used_fallback=False
```

- [ ] **Step 3.2: Record validation report**

Create `docs/tmp/2026-05-08-bbox-fallback-validation.md` with sections:

```markdown
# BBox Fallback Validation

## Problem

Tiny/blank renders were caused by inflated authored USD extents driving oversized renderer bboxes.

## Investigation

Summarize the known bad and control assets, including old/new bbox diagonals from the validation command.

## Solution

`compute_bbox()` now keeps `ComputeWorldBound()` by default but falls back to transformed mesh-point bounds plus visible default-purpose non-mesh `UsdGeom.Boundable` bounds when authored bbox diagonal is at least `5.0x` larger.

## Results

List exact test commands and outputs.

## Risks

Point traversal may add overhead; run small-batch render timing before DLC-scale rerendering.
```

## Task 4: Optional Small Render Validation

**Files:**
- Modify: `docs/tmp/2026-05-08-bbox-fallback-validation.md`

- [ ] **Step 4.1: Try a three-asset temporary render if Isaac Sim is available**

Run one asset at a time to avoid confusing failures:

```bash
export PYTHONPATH="$PYTHONPATH:$(pwd)/src"
export OMNI_KIT_ACCEPT_EULA=YES
python -m render_usd.cli single --usd_path /cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets/basket/040600389fdab577a5376c28e6c5eb15/usd/040600389fdab577a5376c28e6c5eb15.usd --output_dir docs/tmp/bbox-fallback-render-validation/tiny_basket --naming_style view --overwrite
```

Expected result: render command exits `0` and writes `front.png`, `left.png`, `back.png`, `right.png` under the temporary output directory.

- [ ] **Step 4.2: If render cannot run locally, document the blocker and continue**

If Isaac Sim or conda activation is unavailable, record the exact error in `docs/tmp/2026-05-08-bbox-fallback-validation.md`. Do not block the code fix on local GPU rendering.

## Task 5: Review, Iterate, and Final Verification

**Files:**
- Review: `src/render_usd/utils/usd_utils/prim_utils.py`
- Review: `tests/test_prim_utils_bbox.py`
- Review: `docs/tmp/2026-05-08-bbox-fallback-validation.md`

- [ ] **Step 5.1: Request code review**

Dispatch a reviewer with this scope:

```text
Review the bbox fallback implementation in src/render_usd/utils/usd_utils/prim_utils.py, tests/test_prim_utils_bbox.py, and docs/tmp/2026-05-08-bbox-fallback-validation.md. Focus on USD transform correctness, fallback threshold safety, invalid point handling, performance risk, and project import constraints.
```

- [ ] **Step 5.2: Fix Critical and Important review findings**

Apply only targeted fixes. Re-run focused tests after each fix.

- [ ] **Step 5.3: Run final verification**

Run:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q
python -m compileall src/render_usd/utils/usd_utils/prim_utils.py
git status --short
```

Expected result: tests pass, compileall exits `0`, and git status shows only intended bbox fallback files.

## Plan Self-Review

- Spec coverage: the plan implements the conservative renderer-side fallback geometry bbox, validation on known bad/control assets, and documentation.
- Placeholder scan: no placeholder implementation steps remain.
- Type consistency: helper names and `compute_bbox()` parameters are consistent across tests, implementation, and validation commands.
- Scope: limited to `prim_utils.py`, focused tests, and validation docs; no renderer camera-angle, DLC, or asset mutation changes.
