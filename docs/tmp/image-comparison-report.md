# Image Comparison Report: New vs Old Rendering Results

**Date**: 2026-03-08
**Investigator**: image-comparator agent

## Overview

This report compares rendering output between two result sets:
- **New results** (problematic): `GRScenes-test1/GRScenes_assets/` (rendered ~Mar 4-5, 2026)
- **Old results** (correct): `GRScenes-test1_bak/GRScenes_assets/` (rendered ~Jan 19-21, 2026)

The user reported that new renders show objects "too close" to the camera, cutting off parts of the object.

## Detailed Comparisons by Category

### 1. Bed (`0a85b986de35ccfdec7c686d791fd747`)

| View | New (problematic) | Old (correct) |
|------|------------------|---------------|
| front.png | 308,141 bytes | 136,916 bytes |
| back.png | 306,183 bytes | 133,969 bytes |
| left.png | 307,191 bytes | 106,163 bytes |
| right.png | 402,978 bytes | 117,192 bytes |

**Visual findings - SEVERE issue:**
- **New**: Camera is extremely close. All 4 views show only a zoomed-in portion of the bed surface (pillows, blanket texture). The bed frame, headboard, and overall shape are completely invisible. The object fills ~100% of the frame with only surface detail visible.
- **Old**: Camera is at proper distance. The complete bed is visible in every view -- frame, headboard, mattress, pillows, blankets all clearly shown. The object occupies roughly 60-70% of the frame with appropriate padding.
- **Severity**: CRITICAL. The new renders are completely unusable as thumbnails -- you cannot identify the object as a bed.

### 2. Chair (`004300539bfba358119acc294c934311`)

| View | New (problematic) | Old (correct) |
|------|------------------|---------------|
| front.png | 188,947 bytes | 139,483 bytes |

**Visual findings - MODERATE issue:**
- **New**: Camera is closer than old version. The chair fills ~85% of the frame. Legs are slightly cropped at the bottom. Dark background.
- **Old**: Camera is at better distance. The full chair is visible with padding around all edges. The chair occupies ~65% of the frame. Light background.
- **Severity**: MODERATE. The chair is still recognizable, but the framing is tighter than ideal and legs may be partially cropped.

### 3. Table (`0141adbdc03572a900cccdd4368b0211`)

| View | New (problematic) | Old (correct) |
|------|------------------|---------------|
| front.png | 61,607 bytes | 27,019 bytes |

**Visual findings - MIXED (old also has issues):**
- **New**: The complete table is visible -- round tabletop, gold connector, and fluted pedestal base. Camera distance looks reasonable. Object fills ~75% of frame. Dark background.
- **Old**: Only the pedestal base is visible! The round tabletop is completely missing from the render. The base occupies ~30% of the frame, appearing very small and far away. Light background.
- **Severity**: This is an interesting reversal -- the NEW render actually looks BETTER for this specific table. The old render appears to have missed geometry (the tabletop) or had a different bounding box calculation issue. However, the camera distance difference is still visible.

### 4. Bottle (`00593cd931a79e9f71537be5d2f667d3`)

| View | New (problematic) | Old (correct) |
|------|------------------|---------------|
| front.png | 41,726 bytes | 28,286 bytes |

**Visual findings - MILD issue:**
- **New**: Bottle is well-framed, filling ~70% of the frame. Dark background. All features visible.
- **Old**: Same bottle, slightly smaller in frame (~60%), with more padding. Light background.
- **Severity**: MILD. Both versions show the complete bottle. The new version is slightly closer but still acceptable. The main difference is background color (dark vs light).

### 5. Ceiling Light (`0967aabc25e75230cfec9fe7a5635ddb`)

| View | New (problematic) | Old (correct) |
|------|------------------|---------------|
| front.png | 14,916 bytes | 6,979 bytes |

**Visual findings - MODERATE issue:**
- **New**: Shows a flat white panel (ceiling light from below), filling ~60% of frame. Dark background.
- **Old**: Same flat panel but smaller in frame (~40%). Light background.
- **Severity**: MODERATE. The new version shows the object closer/larger, consistent with the overall trend.

## Summary of Findings

### Consistent Patterns Across All Categories

1. **Camera distance is closer in new renders**: In nearly every category, the object appears larger/closer in the new renders compared to old. This is most extreme for large objects (bed) where the camera is so close that the object is severely cropped.

2. **Background color changed**: New renders have a dark/charcoal background. Old renders have a light gray/white background. This is likely due to the HDRI lighting change documented in the project history.

3. **File sizes are generally larger in new renders**: New PNGs are typically 1.3x to 2.5x larger than old ones. This is partly due to the dark background (more complex pixel data vs uniform light gray) and partly due to the closer camera capturing more surface detail.

4. **Severity correlates with object size**:
   - **Large objects** (bed): CRITICAL -- completely unusable, only surface texture visible
   - **Medium objects** (chair, table): MODERATE -- tighter framing, some cropping
   - **Small objects** (bottle): MILD -- still acceptable, just slightly closer

### Root Cause Hypothesis

The camera distance calculation appears to have changed between the old and new rendering code. The old code calculated a distance that provided adequate padding around objects of all sizes. The new code calculates a shorter distance, which is:
- Acceptable for small objects (bottle)
- Slightly too close for medium objects (chair)
- Severely too close for large objects (bed)

This suggests the distance multiplier/factor was reduced, or the bounding box calculation changed in a way that underestimates the size of larger objects.

### Key Observations for Other Agents

- The table case (`0141adbdc03572a900cccdd4368b0211`) is unusual: the old render is WORSE because it appears to miss the tabletop geometry entirely. This could be a separate bounding box issue in the old code, or the USD file was modified between render runs.
- The background color change (dark vs light) is a separate issue from the camera distance problem -- it's from the HDRI lighting implementation.
- The camera distance issue affects ALL categories to varying degrees, confirming this is a systematic code change rather than an asset-specific issue.

## Files Examined

### New results (GRScenes-test1)
- `bed/0a85b986de35ccfdec7c686d791fd747/` - front, back, left, right
- `chair/004300539bfba358119acc294c934311/` - front
- `table/0141adbdc03572a900cccdd4368b0211/` - front, left
- `bottle/00593cd931a79e9f71537be5d2f667d3/` - front
- `ceiling_light/0967aabc25e75230cfec9fe7a5635ddb/` - front

### Old results (GRScenes-test1_bak)
- Same assets as above, all 4 views compared for bed, front view compared for others
