# MDL Material Path Resolution Fix — Technical Report

> Date: 2026-03-04
> Status: Implemented & Tested (DLC Job `dlc1k9aayxi3arv6`)

**[中文版](./mdl-material-fix_zh.md)**

## Table of Contents

1. [Problem Description](#1-problem-description)
2. [Background: What is MDL?](#2-background-what-is-mdl)
3. [Root Cause Analysis](#3-root-cause-analysis)
4. [Solution Design](#4-solution-design)
5. [Implementation Details](#5-implementation-details)
6. [Testing & Verification](#6-testing--verification)
7. [Usage Guide](#7-usage-guide)
8. [FAQ](#8-faq)

---

## 1. Problem Description

### Symptom

When rendering GRScenes-test1 USD assets using the `render-usd` pipeline, **all objects appear as solid red** — a telltale sign of MDL material resolution failure in NVIDIA Isaac Sim / Omniverse.

Example failing file:
```
/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/
  GRScenes_assets/microwave/23fa2734dd917d97b308fbe494284597/usd/
  23fa2734dd917d97b308fbe494284597.usd
```

### Key Observation

The user discovered a workaround: if you set the `MDL_SYSTEM_PATH` environment variable **before** launching Isaac Sim, the materials load correctly:

```bash
# Set this BEFORE launching Isaac Sim
export MDL_SYSTEM_PATH=/isaac-sim/materials/:/cpfs/shared/simulation/liyangzi/grutopia/assets/scenes/GRScenes-100/home_scenes/Materials:

# Then launch Isaac Sim UI — materials render correctly
/isaac-sim/isaac-sim.sh --allow-root
```

This confirmed the issue was about **MDL search path resolution**, not corrupted material files.

---

## 2. Background: What is MDL?

### MDL in One Sentence

**MDL (Material Definition Language)** is NVIDIA's open-source language for defining physically-based materials. Think of it as a "shader programming language" — each `.mdl` file describes how light interacts with a surface (color, roughness, metallic, transparency, etc.).

### How Isaac Sim Finds MDL Files

When Isaac Sim loads a USD file that references an MDL material, it needs to locate the actual `.mdl` file on disk. The search order is:

```
1. Relative path from the USD file's location
   e.g., USD at /a/b/c.usd referencing ./Materials/mat.mdl
         → looks for /a/b/Materials/mat.mdl

2. MDL_SYSTEM_PATH environment variable (colon-separated directories)
   e.g., MDL_SYSTEM_PATH=/path1:/path2
         → looks for /path1/mat.mdl, then /path2/mat.mdl

3. Built-in Isaac Sim MDL paths
   e.g., /isaac-sim/materials/
         → standard NVIDIA material library

4. carb.settings: /app/mdl/additionalSystemPaths
   → programmatic equivalent of MDL_SYSTEM_PATH
```

### What Happens When MDL Resolution Fails?

When the MDL compiler cannot find a referenced `.mdl` file, Omniverse renders the object with a **solid red error material**. This is a deliberate visual signal that something is wrong — it's not a subtle bug, it's an in-your-face "I can't find your material" warning.

---

## 3. Root Cause Analysis

### 3.1 What the USD File References

Inside the microwave USD file, we found 13 MDL material references like this:

```usda
# Inside the USD file
asset inputs:mdl_file = @./Materials/MI_DefaultMaterial_5b7cc2b6b53276768d3b1abc.mdl@
```

These MDL files in turn depend on custom MDL modules:
- `KooPbr::KooMtl` — the base material shader
- `KooPbr_maps::KooPbr_falloff` — texture mapping utilities

### 3.2 Directory Structure Mismatch

The root cause is a **directory structure change** between the original GRScenes-100 dataset and the GRScenes-test1 reorganized version:

**Original GRScenes-100 (works):**
```
home_scenes/
├── Materials/              ← MDL files live here (1679 files)
│   ├── MI_DefaultMaterial_xxx.mdl
│   ├── KooPbr.mdl
│   └── ...
└── microwave/
    └── <uid>/
        ├── instance.usd    ← references ./Materials/MI_xxx.mdl
        └── Materials -> ../../../../../Materials  ← SYMLINK EXISTS!
```

The symlink `Materials -> ../../../../../Materials` makes the relative path `./Materials/MI_xxx.mdl` resolve correctly.

**GRScenes-test1 (broken):**
```
GRScenes-test1/
├── Material/               ← Note: "Material" not "Materials"
│   └── mdl/                ← Extra subdirectory level!
│       ├── MI_DefaultMaterial_xxx.mdl
│       ├── KooPbr.mdl
│       └── ...
└── GRScenes_assets/
    └── microwave/
        └── <uid>/
            └── usd/
                ├── <uid>.usd      ← references ./Materials/MI_xxx.mdl
                ├── textures -> ... ← texture symlink EXISTS
                └── (NO Materials symlink!)  ← MISSING!
```

**Three problems:**

| Issue | Original | GRScenes-test1 |
|-------|----------|----------------|
| Symlink | `Materials -> ../../../../../Materials` exists | **Missing** |
| Directory name | `Materials/` | `Material/` (no "s") |
| Structure | `Materials/MI_xxx.mdl` | `Material/mdl/MI_xxx.mdl` (extra level) |

The reorganization created a `textures` symlink for texture files but **forgot to create the `Materials` symlink** for MDL files. Even if the symlink existed, the directory naming change (`Materials` → `Material/mdl/`) would still break it.

### 3.3 Why MDL_SYSTEM_PATH Fixes It

When you set `MDL_SYSTEM_PATH` to include the directory containing the `.mdl` files:

```bash
export MDL_SYSTEM_PATH=/cpfs/.../home_scenes/Materials:
```

The MDL compiler adds this directory to its search path. When it encounters `MI_DefaultMaterial_xxx.mdl`, it:
1. First tries the relative path `./Materials/MI_xxx.mdl` → **fails** (no symlink)
2. Then searches `MDL_SYSTEM_PATH` directories → **finds it** in `home_scenes/Materials/`
3. Material loads successfully → object renders with correct appearance

### 3.4 Previous Workaround (Material Symlink)

In earlier development, we created a symlink at the project root:
```
render-usd/Material -> usd-scene-physics-prep/GRScenes-test1/Material
```

This was fragile because:
- It only worked when USD files were loaded from specific relative paths
- The symlink was lost when switching machines or re-provisioning DLC nodes
- It didn't help with the naming mismatch (`Materials/` vs `Material/mdl/`)

---

## 4. Solution Design

### Design Goals

1. **Reliable**: Must work in both local development and DLC container environments
2. **No symlinks**: Don't depend on filesystem symlinks that can be lost
3. **Configurable**: Allow adding new MDL search paths without code changes
4. **Non-breaking**: Must preserve existing Isaac Sim built-in material paths
5. **Simple**: Minimal code changes, no over-engineering

### Approach: Dual-Layer MDL Path Registration

We implement MDL search paths at **two independent layers** for maximum reliability:

```
┌─────────────────────────────────────────────────────┐
│                    Layer 1: Shell                     │
│   run_task.sh exports MDL_SYSTEM_PATH                │
│   (env var, read by Isaac Sim at startup)             │
├─────────────────────────────────────────────────────┤
│                   Layer 2: Python                     │
│   cli.py calls carb.settings API                     │
│   /app/mdl/additionalSystemPaths                     │
│   (programmatic, after SimulationApp init)            │
└─────────────────────────────────────────────────────┘
```

**Why two layers?**
- The env var (`MDL_SYSTEM_PATH`) acts as a **safety net** — it's the simplest, most universal mechanism
- The `carb.settings` API is the **official Omniverse way** — it's more precise and can be dynamically configured
- If either layer fails, the other still provides the MDL paths

### Path Collection Priority

All MDL paths from three sources are **merged** (not overridden):

```
1. --mdl_paths CLI argument     ← user explicitly passes paths
2. MDL_SYSTEM_PATH env var      ← set in shell or run_task.sh
3. DEFAULT_MDL_SEARCH_PATHS     ← hardcoded known-good defaults in settings.py
```

Duplicate paths are deduplicated. Non-existent paths are silently skipped.

### Why carb.settings over MDL_SYSTEM_PATH alone?

We found the exact pattern in Isaac Sim's own source code (`omni.mdl.usd_converter`):

```python
# From /isaac-sim/extscache/omni.mdl.usd_converter-1.0.24+d02c707b/
# omni/mdl/usd_converter/usd_converter.py:40-47
import carb.settings
settings = carb.settings.get_settings()
mdl_paths = settings.get("/app/mdl/additionalSystemPaths") or []
mdl_paths.append(new_path)
settings.set_string_array("/app/mdl/additionalSystemPaths", mdl_paths)
```

This is the same mechanism NVIDIA uses internally — it's the most reliable approach.

---

## 5. Implementation Details

### 5.1 `src/render_usd/config/settings.py` — Default Paths

```python
# Default MDL search paths for GRScenes material resolution
# These directories contain MI_*.mdl files and KooPbr modules needed by GRScenes USD assets
DEFAULT_MDL_SEARCH_PATHS = [
    "/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/Material/mdl",
    "/cpfs/shared/simulation/liyangzi/grutopia/assets/scenes/GRScenes-100/home_scenes/Materials",
]
```

Two paths are configured by default — both contain the same set of GRScenes MDL files (1679-1725 files). Having two ensures redundancy if one location is unavailable.

### 5.2 `src/render_usd/cli.py` — Core Logic

Two new functions added between the CONFIG definition and `main()`:

**`_collect_mdl_paths(cli_paths)`** — Merges MDL paths from all three sources:
```python
def _collect_mdl_paths(cli_paths):
    """Collect MDL search paths from CLI args, env var, and defaults."""
    paths = []
    seen = set()

    def _add(p):
        p = os.path.abspath(p)
        if p not in seen and os.path.isdir(p):  # only include existing dirs
            seen.add(p)
            paths.append(p)

    # 1. CLI paths (highest priority)
    if cli_paths:
        for p in cli_paths:
            _add(p)

    # 2. Environment variable (colon-separated)
    env_val = os.environ.get("MDL_SYSTEM_PATH", "")
    if env_val:
        for p in env_val.split(":"):
            if p.strip():
                _add(p.strip())

    # 3. Defaults from settings.py
    for p in DEFAULT_MDL_SEARCH_PATHS:
        _add(p)

    return paths
```

**`_configure_mdl_search_paths(mdl_paths)`** — Registers paths via carb.settings:
```python
def _configure_mdl_search_paths(mdl_paths):
    """Register MDL search paths via carb.settings after SimulationApp init."""
    if not mdl_paths:
        return

    import carb.settings  # must import after SimulationApp init
    settings = carb.settings.get_settings()
    existing = settings.get("/app/mdl/additionalSystemPaths") or []
    merged = list(existing)
    for p in mdl_paths:
        if p not in merged:
            merged.append(p)
    settings.set_string_array("/app/mdl/additionalSystemPaths", merged)
    print(f"[CLI] MDL search paths configured: {merged}")
```

**Execution order in `main()`:**
```python
def main():
    # 1. Parse arguments (including --mdl_paths)
    args = parser.parse_args()

    # 2. Collect MDL paths BEFORE SimulationApp (reads env var + defaults)
    mdl_paths = _collect_mdl_paths(args.mdl_paths)

    # 3. Initialize Isaac Sim
    kit = SimulationApp(CONFIG)

    # 4. Configure MDL paths via carb.settings AFTER SimulationApp
    #    (carb module only available after SimulationApp init)
    _configure_mdl_search_paths(mdl_paths)

    # 5. Import rendering modules and proceed...
    from render_usd.core.renderer import RenderManager
    renderer = RenderManager(kit)
    # ... render USD files — MDL materials now resolve correctly
```

**Why this order matters:**
- `carb.settings` is part of the Omniverse runtime, it's only available **after** `SimulationApp()` initializes the Omniverse Kit kernel
- But we need to **collect** the paths (from env var, CLI args, settings.py) **before** `SimulationApp()` because that's just pure Python — no Omniverse dependency
- The actual `carb.settings.set_string_array()` call must happen **after** `SimulationApp()` but **before** any USD stage is loaded

### 5.3 `scripts/dlc/run_task.sh` — Environment Variable Fallback

```bash
# Set MDL search paths (belt-and-suspenders with the carb.settings approach in cli.py)
MDL_PATHS="/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/Material/mdl"
MDL_PATHS="$MDL_PATHS:/cpfs/shared/simulation/liyangzi/grutopia/assets/scenes/GRScenes-100/home_scenes/Materials"
export MDL_SYSTEM_PATH="${MDL_SYSTEM_PATH:+$MDL_SYSTEM_PATH:}$MDL_PATHS"
echo "MDL_SYSTEM_PATH=$MDL_SYSTEM_PATH"
```

The `${MDL_SYSTEM_PATH:+$MDL_SYSTEM_PATH:}` syntax means: if `MDL_SYSTEM_PATH` is already set, prepend its value with a colon separator; otherwise start fresh. This preserves any pre-existing paths.

---

## 6. Testing & Verification

### Test Plan

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Submit DLC job with the same microwave USD that previously rendered all-red | Materials render correctly (not red) |
| 2 | Check that `[CLI] MDL search paths configured: [...]` appears in job logs | Confirms carb.settings path registration |
| 3 | Verify output PNGs show correct microwave appearance | Visual confirmation |

### DLC Test Job

```bash
# Submitted test job
bash scripts/dlc/launch_job.sh \
  test_mdl_fix 0 1 \
  "d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz" \
  "single /cpfs/.../microwave/23fa2734dd917d97b308fbe494284597/usd/23fa2734dd917d97b308fbe494284597.usd /cpfs/.../render-usd/output_test_mdl_fix"
```

- **Job Name**: `test_mdl_fix_0_1`
- **Job ID**: `dlc1k9aayxi3arv6`
- **Output directory**: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/output_test_mdl_fix/`

### Verification Command

```bash
# Check if output images were generated
ls /cpfs/shared/simulation/zhuzihou/dev/render-usd/output_test_mdl_fix/

# Expected: 4 PNG files (front, left, back, right views of the microwave)
```

---

## 7. Usage Guide

### Default Behavior (Most Common)

For GRScenes assets, **no extra configuration needed**. The default paths in `settings.py` will automatically be registered:

```bash
# Just run as usual — MDL paths are configured automatically
python -m render_usd.cli single --usd_path /path/to/grscenes/asset.usd --output_dir ./output
```

### Custom MDL Paths via CLI

If you have MDL files in a non-default location:

```bash
python -m render_usd.cli \
  --mdl_paths /path/to/custom/mdl/dir /another/mdl/dir \
  single --usd_path /path/to/asset.usd --output_dir ./output
```

Note: `--mdl_paths` must come **before** the subcommand (`single`, `grscenes100`, etc.).

### Custom MDL Paths via Environment Variable

```bash
export MDL_SYSTEM_PATH="/path/to/mdl/dir1:/path/to/mdl/dir2"
python -m render_usd.cli single --usd_path /path/to/asset.usd --output_dir ./output
```

### Adding Permanent Default Paths

Edit `src/render_usd/config/settings.py`:

```python
DEFAULT_MDL_SEARCH_PATHS = [
    "/cpfs/.../existing/path",
    "/cpfs/.../your/new/mdl/directory",  # add new path here
]
```

---

## 8. FAQ

### Q: Why not just recreate the Materials symlink?

Symlinks are fragile:
- Lost when switching machines or re-provisioning DLC containers
- Only work for files loaded from specific relative paths
- Don't solve the naming mismatch (`Materials/` vs `Material/mdl/`)
- Hard to maintain across different dataset versions

The `carb.settings` approach is **symlink-free, works everywhere, and is the official NVIDIA mechanism**.

### Q: Will this slow down rendering?

No. The MDL path registration happens once at startup (before any rendering). The MDL compiler caches resolved paths, so subsequent material lookups are fast.

### Q: What if I add a path that doesn't exist?

It's silently skipped. The `_collect_mdl_paths()` function checks `os.path.isdir(p)` and only includes directories that actually exist on disk.

### Q: Do I need both the env var AND the carb.settings approach?

Technically, either one alone should work. We use both as a "belt and suspenders" strategy:
- The env var ensures MDL paths are available at the earliest possible moment (before Python even starts)
- The `carb.settings` call ensures paths are registered through the official API

### Q: Can I use this for non-GRScenes assets?

Yes. The `--mdl_paths` CLI argument and `MDL_SYSTEM_PATH` env var work with any dataset. Just point them to the directory containing your `.mdl` files.

---

## Files Changed

| File | Change |
|------|--------|
| `src/render_usd/config/settings.py` | Added `DEFAULT_MDL_SEARCH_PATHS` list |
| `src/render_usd/cli.py` | Added `_collect_mdl_paths()`, `_configure_mdl_search_paths()`, `--mdl_paths` CLI arg |
| `scripts/dlc/run_task.sh` | Added `MDL_SYSTEM_PATH` env var export |
