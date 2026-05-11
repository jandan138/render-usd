import numpy as np
import pytest
from pxr import Gf, Usd, UsdGeom

from render_usd.utils.usd_utils import prim_utils
from render_usd.utils.usd_utils.prim_utils import compute_bbox


def _define_mesh(stage, path, points=None, extent=None, translate=None):
    mesh = UsdGeom.Mesh.Define(stage, path)
    if points is not None:
        mesh.CreatePointsAttr(points)
    if points is not None and len(points) >= 3:
        mesh.CreateFaceVertexCountsAttr([3])
        mesh.CreateFaceVertexIndicesAttr([0, 1, 2])
    if extent is not None:
        mesh.CreateExtentAttr(extent)
    if translate is not None:
        UsdGeom.Xformable(mesh.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(*translate))
    return mesh


def _root_with_mesh(points=None, extent=None, translate=None, root_translate=None):
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    if root_translate is not None:
        UsdGeom.Xformable(root.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(*root_translate))
    _define_mesh(stage, "/Root/Mesh", points=points, extent=extent, translate=translate)
    return stage, root.GetPrim()


def test_ratio_below_threshold_keeps_authored_bbox():
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-1.9, -1.9, -1.9), (2.9, 2.9, 2.9)],
    )

    bbox = compute_bbox(prim)

    np.testing.assert_allclose(bbox, [[-1.9, -1.9, -1.9], [2.9, 2.9, 2.9]])


def test_inflated_authored_bbox_above_threshold_uses_mesh_point_bbox():
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )

    bbox = compute_bbox(prim)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [1, 1, 1]])


def test_shifted_authored_bbox_center_uses_mesh_point_bbox():
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (2, 0, 0), (0, 2, 2)],
        extent=[(100, 100, 100), (102, 102, 102)],
    )

    bbox = compute_bbox(prim)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [2, 2, 2]])


def test_exact_default_threshold_triggers_mesh_point_fallback():
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-2, -2, -2), (3, 3, 3)],
    )

    bbox = compute_bbox(prim)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [1, 1, 1]])


def test_lowered_threshold_overrides_default_cutoff():
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-1.5, -1.5, -1.5), (2.5, 2.5, 2.5)],
    )

    default_bbox = compute_bbox(prim)
    lowered_threshold_bbox = compute_bbox(prim, extent_fallback_ratio=3.0)

    np.testing.assert_allclose(default_bbox, [[-1.5, -1.5, -1.5], [2.5, 2.5, 2.5]])
    np.testing.assert_allclose(lowered_threshold_bbox, [[0, 0, 0], [1, 1, 1]])


def test_mesh_world_transform_is_applied_before_fallback():
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        extent=[(-10, -10, -10), (10, 10, 10)],
        translate=(10, 20, 30),
    )

    bbox = compute_bbox(prim, extent_fallback_ratio=2.0)

    np.testing.assert_allclose(bbox, [[10, 20, 30], [11, 21, 30]])


def test_ancestor_transform_is_applied_before_fallback():
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
        root_translate=(10, 20, 30),
    )

    bbox = compute_bbox(prim)

    np.testing.assert_allclose(bbox, [[10, 20, 30], [11, 21, 31]])


def test_recursive_mesh_point_fallback_unions_multiple_meshes():
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    _define_mesh(
        stage,
        "/Root/MeshA",
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    UsdGeom.Xform.Define(stage, "/Root/Group")
    _define_mesh(
        stage,
        "/Root/Group/MeshB",
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
        translate=(10, 10, 10),
    )

    bbox = compute_bbox(root.GetPrim(), extent_fallback_ratio=2.0)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [11, 11, 11]])


def test_fallback_can_be_disabled():
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )

    bbox = compute_bbox(
        prim,
        extent_fallback_ratio=2.0,
        use_mesh_point_fallback=False,
    )

    np.testing.assert_allclose(bbox, [[-10, -10, -10], [10, 10, 10]])


def test_missing_or_empty_mesh_points_keep_authored_bbox():
    missing_points_stage, missing_points_prim = _root_with_mesh(
        points=None,
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    empty_points_stage, empty_points_prim = _root_with_mesh(
        points=[],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )

    missing_bbox = compute_bbox(missing_points_prim, extent_fallback_ratio=2.0)
    empty_bbox = compute_bbox(empty_points_prim, extent_fallback_ratio=2.0)

    np.testing.assert_allclose(missing_bbox, [[-10, -10, -10], [10, 10, 10]])
    np.testing.assert_allclose(empty_bbox, [[-10, -10, -10], [10, 10, 10]])


def test_invalid_mesh_points_are_ignored():
    stage, prim = _root_with_mesh(
        points=[
            (0, 0, 0),
            (1, 0, 0),
            (0, 1, 0),
            (float("nan"), 100, 100),
            (100, float("inf"), 100),
        ],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )

    bbox = compute_bbox(prim, extent_fallback_ratio=2.0)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [1, 1, 0]])


def test_malformed_mesh_points_are_skipped(monkeypatch):
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    original_to_list = prim_utils.to_list

    def malformed_points(data):
        result = original_to_list(data)
        if result and result[0] == Gf.Vec3f(0, 0, 0):
            return ["not-a-point"]
        return result

    monkeypatch.setattr(prim_utils, "to_list", malformed_points)

    bbox = compute_bbox(prim, extent_fallback_ratio=2.0)

    np.testing.assert_allclose(bbox, [[-10, -10, -10], [10, 10, 10]])


@pytest.mark.parametrize("extent_fallback_ratio", [0, -1, float("inf"), float("nan")])
def test_invalid_extent_fallback_ratio_raises(extent_fallback_ratio):
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )

    with pytest.raises(ValueError, match="extent_fallback_ratio"):
        compute_bbox(prim, extent_fallback_ratio=extent_fallback_ratio)


def test_invalid_authored_bbox_prefers_finite_mesh_bbox(monkeypatch):
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    monkeypatch.setattr(
        prim_utils,
        "_compute_authored_world_bbox",
        lambda prim: np.array([[float("nan"), 0, 0], [1, 1, 1]]),
    )

    bbox = compute_bbox(prim)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [1, 1, 1]])


def test_mesh_point_fallback_ignores_invisible_meshes():
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    _define_mesh(
        stage,
        "/Root/VisibleMesh",
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    invisible_mesh = _define_mesh(
        stage,
        "/Root/InvisibleMesh",
        points=[(100, 100, 100), (101, 100, 100), (100, 101, 101)],
        extent=[(100, 100, 100), (101, 101, 101)],
    )
    UsdGeom.Imageable(invisible_mesh.GetPrim()).MakeInvisible()

    bbox = compute_bbox(root.GetPrim(), extent_fallback_ratio=2.0)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [1, 1, 1]])


def test_mesh_point_fallback_ignores_non_default_purpose_meshes():
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    _define_mesh(
        stage,
        "/Root/DefaultMesh",
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    render_mesh = _define_mesh(
        stage,
        "/Root/RenderMesh",
        points=[(100, 100, 100), (101, 100, 100), (100, 101, 101)],
        extent=[(100, 100, 100), (101, 101, 101)],
    )
    UsdGeom.Imageable(render_mesh.GetPrim()).CreatePurposeAttr().Set(UsdGeom.Tokens.render)

    bbox = compute_bbox(root.GetPrim(), extent_fallback_ratio=2.0)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [1, 1, 1]])


def test_mesh_point_fallback_ignores_child_of_invisible_parent():
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    _define_mesh(
        stage,
        "/Root/VisibleMesh",
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    invisible_group = UsdGeom.Xform.Define(stage, "/Root/InvisibleGroup")
    UsdGeom.Imageable(invisible_group.GetPrim()).MakeInvisible()
    _define_mesh(
        stage,
        "/Root/InvisibleGroup/ChildMesh",
        points=[(100, 100, 100), (101, 100, 100), (100, 101, 101)],
        extent=[(100, 100, 100), (101, 101, 101)],
    )

    bbox = compute_bbox(root.GetPrim(), extent_fallback_ratio=2.0)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [1, 1, 1]])


def test_mesh_point_fallback_matches_default_bound_for_parent_purpose():
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    _define_mesh(
        stage,
        "/Root/DefaultMesh",
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    render_group = UsdGeom.Xform.Define(stage, "/Root/RenderGroup")
    UsdGeom.Imageable(render_group.GetPrim()).CreatePurposeAttr().Set(UsdGeom.Tokens.render)
    child_mesh = _define_mesh(
        stage,
        "/Root/RenderGroup/ChildMesh",
        points=[(100, 100, 100), (101, 100, 100), (100, 101, 101)],
        extent=[(100, 100, 100), (101, 101, 101)],
    )

    child_purpose = UsdGeom.Imageable(child_mesh.GetPrim()).ComputePurpose()
    bbox = compute_bbox(root.GetPrim(), extent_fallback_ratio=2.0)

    assert child_purpose == UsdGeom.Tokens.render
    np.testing.assert_allclose(bbox, [[0, 0, 0], [1, 1, 1]])


def test_invalid_authored_bbox_keeps_invalid_bbox_for_zero_size_mesh(monkeypatch):
    stage, prim = _root_with_mesh(
        points=[(0, 0, 0), (0, 0, 0), (0, 0, 0)],
        extent=[(-10, -10, -10), (10, 10, 10)],
    )
    invalid_authored_bbox = np.array([[float("nan"), 0, 0], [1, 1, 1]])
    monkeypatch.setattr(
        prim_utils,
        "_compute_authored_world_bbox",
        lambda prim: invalid_authored_bbox,
    )

    bbox = compute_bbox(prim)

    np.testing.assert_allclose(bbox, invalid_authored_bbox)


def test_fallback_includes_visible_default_non_mesh_boundable_bounds():
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    _define_mesh(
        stage,
        "/Root/Mesh",
        points=[(0, 0, 0), (1, 0, 0), (0, 1, 1)],
        extent=[(-20, -20, -20), (20, 20, 20)],
    )
    cube = UsdGeom.Cube.Define(stage, "/Root/Cube")
    cube.CreateSizeAttr(2.0)
    UsdGeom.Xformable(cube.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(10, 10, 10))

    bbox = compute_bbox(root.GetPrim(), extent_fallback_ratio=2.0)

    np.testing.assert_allclose(bbox, [[0, 0, 0], [11, 11, 11]])
