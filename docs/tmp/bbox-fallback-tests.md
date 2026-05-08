# BBox Fallback Tests

## Problem

Add red-state unit coverage for `compute_bbox()` mesh-point fallback behavior without changing production code. Continue the TDD cycle for review feedback covering malformed point payloads, invalid fallback ratios, invalid authored bboxes, memory overhead in mesh bbox aggregation, semantic alignment with authored `ComputeWorldBound(..., default_)` filtering, explicit effective visibility handling, zero-size fallback rejection, and visible default-purpose non-mesh boundables.

## Investigation

`compute_bbox()` initially accepted only `prim` and delegated directly to `UsdGeom.Imageable.ComputeWorldBound()`, so fallback-related keyword arguments were not supported. After the first implementation pass, review found that mesh fallback collected every valid transformed point before computing the bbox, malformed points could raise, invalid `extent_fallback_ratio` values were accepted, and invalid authored bboxes were returned even when a finite mesh bbox was available. A later review found a semantic mismatch: authored bbox calculation uses default-purpose world bounds while mesh fallback included invisible and non-default-purpose meshes. Follow-up review requested explicit effective visibility for inherited visibility cases. Current review found that invalid authored bbox handling could return a zero-size fallback bbox, and that fallback could crop visible default-purpose non-mesh `UsdGeom.Boundable` geometry.

## Solution

Added `tests/test_prim_utils_bbox.py` with in-memory USD stages covering threshold behavior, inflated authored extents, exact default-threshold fallback, override-threshold fallback, mesh and ancestor world transforms, recursive multi-mesh union, disabled fallback, missing or empty points, and invalid point filtering. The helper keeps each stage alive for the test and only authors face topology when at least three points are present. The default below-threshold and above-threshold tests use nondegenerate XYZ point spans.

For the review feedback TDD cycle, added tests before production changes for malformed point payload handling, invalid `extent_fallback_ratio` rejection, and invalid authored bbox fallback. Malformed points and invalid authored bbox use monkeypatching because USD typed point attributes do not reliably author those invalid states directly in an in-memory stage.

Updated `src/render_usd/utils/usd_utils/prim_utils.py` to compute mesh bbox incrementally per mesh/subtree, skip malformed mesh point payloads, validate public `extent_fallback_ratio`, and prefer finite mesh bbox when authored bbox is non-finite.

For the visibility/purpose TDD cycle, added in-memory USD tests with visible/default mesh points near origin and invisible/render-purpose helper meshes far away. Updated fallback traversal to skip meshes whose effective visibility computes to invisible and meshes whose computed purpose is not `UsdGeom.Tokens.default_`.

For the effective visibility follow-up, added an inherited parent-invisible test where the child mesh has no local visibility setting. Also added a parent-purpose test and verified `UsdGeom.Imageable(child).ComputePurpose()` resolves the inherited parent `render` purpose, matching `ComputeWorldBound(default_)` exclusion semantics. In this USD build, the exact no-local inherited visibility test already passed before changing production code because `ComputeVisibility(time)` returned the inherited invisible state; the implementation was still updated to call `ComputeEffectiveVisibility(time=...)` explicitly.

For the zero-size/boundable review cycle, added tests before production changes for invalid authored bbox plus coincident mesh points, and for a visible default-purpose `UsdGeom.Cube` away from an inflated mesh. Updated fallback validation to reject non-finite or zero-diagonal fallback bboxes and to include visible default-purpose non-mesh `UsdGeom.Boundable` world bounds in the fallback union while retaining mesh-point fallback for meshes.

## Results

Command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Result after making recursive union fallback explicit: `9 failed, 1 passed in 0.31s`. The default inflated-bbox, exact `5.0x` threshold, and ancestor-transform tests fail by assertion because `compute_bbox(prim)` still returns authored bounds, and the override/fallback-parameter tests, including recursive union with `extent_fallback_ratio=2.0`, fail with `TypeError: compute_bbox() got an unexpected keyword argument 'extent_fallback_ratio'`.

Review feedback RED command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Review feedback RED result: `6 failed, 10 passed in 0.39s`. The malformed payload test failed with `ValueError: could not convert string to float: 'not-a-point'`, all four invalid-ratio parameter cases failed with `Failed: DID NOT RAISE <class 'ValueError'>`, and the invalid authored bbox test returned the monkeypatched non-finite authored bbox instead of the finite mesh bbox.

Review feedback GREEN command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Review feedback GREEN result: `16 passed in 0.33s`.

Compile command: `python -m compileall src/render_usd/utils/usd_utils/prim_utils.py`

Compile result: `Compiling 'src/render_usd/utils/usd_utils/prim_utils.py'...`

Visibility/purpose RED command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Visibility/purpose RED result: `2 failed, 16 passed in 0.31s`. The invisible-mesh and non-default-purpose tests both returned authored bounds `array([[-10., -10., -10.], [10., 10., 10.]])` instead of the near visible/default mesh bbox `[[0, 0, 0], [1, 1, 1]]`, proving the far helper meshes were still included in fallback bbox calculation.

Visibility/purpose GREEN command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Visibility/purpose GREEN result: `18 passed in 0.29s`.

Visibility/purpose compile command: `python -m compileall src/render_usd/utils/usd_utils/prim_utils.py`

Visibility/purpose compile result: `Compiling 'src/render_usd/utils/usd_utils/prim_utils.py'...`

Effective visibility no-local RED command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Effective visibility no-local RED result: `20 passed in 0.30s`. This did not produce a red failure for the exact requested no-local inherited visibility case; USD resolved the child mesh visibility as inherited invisible before the production change.

Effective visibility diagnostic command after temporarily authoring local child `visible` under an invisible parent: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Effective visibility diagnostic result: `1 failed, 19 passed in 0.39s`, with `test_mesh_point_fallback_ignores_child_of_invisible_parent` returning `array([[-10., -10., -10.], [101., 101., 101.]])`. That diagnostic was not kept because USD `ComputeWorldBound(default_)` semantics allow a locally visible child to override inherited invisibility.

Effective visibility GREEN command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Effective visibility GREEN result: `20 passed in 0.33s`.

Effective visibility compile command: `python -m compileall src/render_usd/utils/usd_utils/prim_utils.py`

Effective visibility compile result: `Compiling 'src/render_usd/utils/usd_utils/prim_utils.py'...`

Zero-size/boundable RED command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Zero-size/boundable RED result: `2 failed, 20 passed in 0.37s`. The zero-size mesh test returned `array([[0., 0., 0.], [0., 0., 0.]])` instead of the monkeypatched invalid authored bbox, and the cube test returned `array([[0., 0., 0.], [1., 1., 1.]])` instead of including the cube bound `[[0, 0, 0], [11, 11, 11]]`.

Intermediate boundable implementation command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Intermediate boundable implementation result: `1 failed, 21 passed in 0.31s`. The cube test returned authored bounds `array([[-10., -10., -10.], [11., 11., 11.]])`, which exposed that the test mesh authored extent was not inflated enough after adding the cube to fallback union. The test was adjusted to use `[-20, 20]` mesh extent so the threshold still exercises fallback selection.

Zero-size/boundable GREEN command: `PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py -q`

Zero-size/boundable GREEN result: `22 passed in 0.30s`.

Zero-size/boundable compile command: `python -m compileall src/render_usd/utils/usd_utils/prim_utils.py`

Zero-size/boundable compile result: no output.
