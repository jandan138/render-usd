# MDL Material Fix — Root Cause Correction

> Date: 2026-03-11
> Status: Corrects findings in `mdl-material-fix.md` / `mdl-material-fix_zh.md`

## Summary of Correction

The original report (`mdl-material-fix.md`, 2026-03-04) contained an **incorrect root cause analysis**. This document corrects it based on a comprehensive investigation of 52,907 asset USD files and the composed scene `layout.usd`.

---

## What the Original Report Got Wrong

### Wrong: "MDL relative paths are broken due to directory depth mismatch"

The original report stated that asset USD files reference `./Materials/MI_xxx.mdl` and that the path fails because:
1. The `Materials` symlink is missing
2. Directory renamed from `Materials/` to `Material/mdl/`
3. Extra subdirectory level

### Correct: MDL relative paths are actually correct

**All 52,907 asset USD files** use `../../../../Material/mdl/XXX.mdl` (4 levels up), which resolves correctly:

```
Asset USD location: GRScenes-test1/GRScenes_assets/category/HASH/usd/HASH.usd
                                                                  ↑ start
../../../../ → GRScenes-test1/
→ GRScenes-test1/Material/mdl/XXX.mdl  ← EXISTS, resolves correctly
```

The `textures` symlink in each `usd/` directory also uses the same 4-level depth and works correctly:
```
usd/textures -> ../../../../Material/mdl/textures
```

**The MDL files themselves are found. The relative path resolution is not the problem.**

---

## The Real Root Cause: KooPbr Module Import Failure

### Two MDL Material Systems

The GRScenes dataset uses two distinct MDL material systems:

| System | MDL Files | Asset Coverage | Module Dependency | Isaac Sim Status |
|--------|-----------|---------------|-------------------|------------------|
| **OmniUe4** | `Num*.mdl` (152 files, 9%) | **95.8%** of assets (50,678) | `OmniUe4Base.mdl` | Built-in at `/isaac-sim/kit/mdl/core/Ue4/` |
| **KooPbr** | `MI_*.mdl` + hex-hash (1,567 files, 91%) | **1.2%** of assets (~633) | `KooPbr.mdl`, `KooPbr_maps.mdl` | **NOT built-in** |

### Why Only Some Objects Are Red

The failure chain for KooPbr materials:

```
1. USD references ../../../../Material/mdl/MI_xxx.mdl      ← RESOLVES OK ✅
2. MI_xxx.mdl contains: import ::KooPbr::KooMtl;           ← ABSOLUTE MDL IMPORT
3. Absolute imports (:: prefix) search MDL search paths ONLY
4. Isaac Sim default search paths: /isaac-sim/kit/mdl/...   ← No KooPbr here
5. KooPbr.mdl lives in Material/mdl/ (same dir as MI_xxx.mdl)
   but this dir is NOT in the default MDL search paths
6. → Module resolution fails → MDL compilation fails → RED ❌
```

OmniUe4 materials work because:

```
1. USD references ../../../../Material/mdl/Num_xxx.mdl      ← RESOLVES OK ✅
2. Num_xxx.mdl contains: using .::OmniUe4Base import *;
3. OmniUe4Base.mdl is built into Isaac Sim at:
   /isaac-sim/kit/mdl/core/Ue4/OmniUe4Base.mdl             ← FOUND ✅
4. → Module resolves → MDL compiles → Renders correctly ✅
```

### Verified with Specific Prims

| Prim | Category | Material | MDL System | Renders |
|------|----------|----------|------------|---------|
| `/Root/Meshes/Animation/electriccooker/model_a461b973.../Component_64` | electriccooker | `MI_6577347511bd150001eb1e49.mdl` | KooPbr | RED ❌ |
| `/Root/Meshes/Animation/faucet/model_893d5289.../Component_2` | faucet | `MI_6526db6102ca60000190060f.mdl` | KooPbr | RED ❌ |
| `/Root/Meshes/Furnitures/chair/model_2096523e.../SM_02_obj3_0` | chair | `Num5dd77cea7d6a630001bffad3.mdl` | OmniUe4 | OK ✅ |
| `/Root/Meshes/BaseAnimation/cabinet/model_17fc6491.../...` | cabinet | `Num5dd77cea7d6a630001bffad3.mdl` | OmniUe4 | OK ✅ |

---

## Affected Categories (18 high-risk, >20% KooPbr assets)

| Category | KooPbr % | Category | KooPbr % |
|----------|----------|----------|----------|
| chest_of_drawers | 69% | shoe_cabinet | 43% |
| sideboard_cabinet | 60% | washing_machine | 42% |
| oven | 52% | microwave | 41% |
| electric_cooker | 46% | pan | 40% |
| desk | 45% | toilet | 39% |
| hearth | 43% | faucet | 38% |
| dish_washer | 35% | pot | 31% |
| refrigerator | 33% | tea_table | 30% |
| trash_can | 32% | night_stand | 27% |

36 categories have 0% KooPbr and will always render correctly.

---

## Fix Remains the Same

The fix implemented in `cli.py` (registering `Material/mdl/` via `carb.settings` `/app/mdl/additionalSystemPaths`) is correct and addresses the real root cause:

```python
# This makes KooPbr.mdl discoverable via MDL search paths
settings.set_string_array("/app/mdl/additionalSystemPaths", [
    ".../GRScenes-test1/Material/mdl",  # KooPbr.mdl lives here
    ...
])
```

For Isaac Sim GUI (without the render pipeline):
```bash
export MDL_SYSTEM_PATH="/cpfs/.../GRScenes-test1/Material/mdl"
/isaac-sim/isaac-sim.sh --allow-root
```

---

## Dataset Statistics

- **Total asset USD files**: 52,907 (across 79 categories)
- **Total MDL files**: 1,725 in `Material/mdl/`
- **Total texture files**: 20,465 in `Material/mdl/textures/`
- **Uniform directory structure**: All assets at `GRScenes_assets/Category/HASH/usd/HASH.usd` (depth 5)
- **Uniform symlinks**: All 52,907 `usd/` dirs have `textures -> ../../../../Material/mdl/textures` (no Materials symlink in any)
- **Scene files**: `GRScenes100/` layout.usd files override MDL paths to `../../../Material/mdl/` (3 levels, correct from their location)
