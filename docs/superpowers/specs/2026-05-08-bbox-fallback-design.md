# Design: Fallback Geometry BBox for Inflated USD Extents

## Problem

Some GRScenes assets render as tiny or nearly blank even though all four PNG files are present. Diagnosis showed that affected USD files can contain stale or mis-scaled authored mesh `extent` metadata. `compute_bbox()` currently calls `UsdGeom.Imageable.ComputeWorldBound()`, which trusts those extents. The renderer then places cameras using the oversized bbox diagonal, so the visible geometry is framed from too far away.

Known examples:

- Tiny basket: authored bbox diagonal `636.184620`, transformed mesh-point diagonal `62.323327`.
- Blank basket: authored bbox diagonal `4239.049048`, transformed mesh-point diagonal `42.769519`.
- Normal backpack control: authored bbox diagonal and mesh-point diagonal both `76.540939`.

## Goal

Make renderer camera placement robust to inflated authored USD extents by using a fallback geometry bbox when authored bounds are substantially larger than real visible default-purpose geometry.

## Non-Goals

- Do not modify USD assets on disk.
- Do not change camera sampling angles, image naming, skip logic, lighting, or DLC scripts.
- Do not treat every `suspicious` image-quality result as a renderer failure.
- Do not add Isaac Sim imports at module top level beyond existing project patterns.

## Considered Approaches

### Approach A: Lower camera distance multiplier

This is the smallest renderer change, but it treats the symptom after the bbox is already wrong. It risks over-zooming normal assets and still fails when the center is distorted by bad extents.

### Approach B: Preprocess USD extents

This fixes assets once, but it mutates source data and requires a separate asset-management workflow. It is riskier for shared datasets and does not protect future bad assets.

### Approach C: Renderer-side fallback geometry bbox

This keeps source assets unchanged and fixes the value the camera actually needs. It can be guarded by a conservative ratio threshold so normal assets keep the current `ComputeWorldBound()` behavior. This is the recommended approach.

## Chosen Design

Add a fallback path inside `src/render_usd/utils/usd_utils/prim_utils.py`:

1. Compute the current authored/world bbox using `UsdGeom.Imageable.ComputeWorldBound()`.
2. Recursively collect fallback geometry under the target prim.
3. For each visible default-purpose mesh, transform local points to world space using `UsdGeom.Imageable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default())`.
4. For each visible default-purpose non-mesh `UsdGeom.Boundable`, include its USD world bound so fallback does not crop valid non-mesh geometry.
5. Build a union fallback bbox from finite transformed mesh points and valid non-mesh boundable bounds.
6. Compare bbox diagonals.
7. If the authored bbox diagonal is at least `5.0x` larger than the fallback geometry bbox diagonal, return the fallback geometry bbox.
8. Otherwise return the current authored/world bbox.
9. If a valid fallback bbox cannot be computed, return the current authored/world bbox.

The default threshold is `5.0` because the known bad examples are roughly `10x` and `99x`, while the normal control is `1x`. This avoids aggressive behavior changes for modest differences that may be intentional.

## Components

- `compute_bbox(prim, use_mesh_point_fallback=True, extent_fallback_ratio=5.0)`: public bbox helper used by renderer. Existing callers can keep calling `compute_bbox(prim)`.
- `_compute_authored_world_bbox(prim)`: existing authored/world bbox behavior extracted for testability.
- `_compute_mesh_point_bbox(prim)`: private recursive helper that returns a fallback geometry bbox or `None`. Meshes use transformed points; visible default-purpose non-mesh `UsdGeom.Boundable` prims contribute their USD world bounds so fallback does not crop valid non-mesh geometry.
- `_is_valid_fallback_bbox(bbox)`: validates finite values and positive diagonal before a fallback bbox can replace authored bounds.

## Data Flow

```text
RenderManager
  -> compute_bbox(usd_prim)
     -> authored bbox from ComputeWorldBound
     -> fallback geometry bbox from transformed mesh points plus non-mesh boundable bounds
     -> ratio gate chooses authored bbox or fallback geometry bbox
  -> camera center and distance from returned bbox
  -> four-view render
```

## Error Handling

- Empty prims, non-mesh prims, missing point arrays, empty point arrays, NaN points, and Inf points do not crash bbox computation.
- If fallback computation fails or produces an invalid bbox, `compute_bbox()` returns the original authored/world bbox.
- Existing renderer NaN/Inf checks remain responsible for skipping truly invalid final bboxes.

## Testing

Add unit tests that do not require Isaac Sim:

- Normal authored bbox ratio below threshold returns authored bbox.
- Inflated authored bbox ratio above threshold returns fallback geometry bbox.
- Mesh transform is applied before computing fallback bbox.
- Missing or empty mesh points return authored bbox.
- NaN/Inf mesh points are ignored.
- Fallback can be disabled for compatibility.

Add focused validation using real USD assets in the `render-usd` conda environment:

- Tiny basket should report fallback bbox diagonal near `62.323327`.
- Blank basket should report fallback bbox diagonal near `42.769519`.
- Normal backpack should keep authored bbox diagonal near `76.540939`.

If Isaac Sim rendering is available, run a small overwrite render for these three assets into a temporary output directory and re-run the image quality screener against the outputs.

## Risks

- Point traversal may be slower than authored extent lookup. This is acceptable for fallback validation, but full DLC impact should be measured before large-scale rerendering.
- Some assets may intentionally use authored bounds larger than visible points. The conservative `5.0x` threshold reduces this risk.
- Meshes with time-sampled points or non-default purposes are not fully modeled by this minimal fix. The renderer currently uses default time and default purpose, so this matches existing behavior.

## Acceptance Criteria

- Unit tests pass with system Python where possible.
- `compileall` passes for modified Python files.
- Real-asset bbox validation confirms fallback on the two bad baskets and no fallback on the normal backpack control.
- Documentation records problem, root cause, solution, validation commands, results, and remaining risks.
