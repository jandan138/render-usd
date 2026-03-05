# Git Commit Record: Duplicate Code Fix

## Commit Information

### Commit 1: Main Fix
- **Commit Hash**: `8c1eb14`
- **Branch**: main
- **Date**: 2026-03-05
- **Author**: version-commit-agent

### Commit 2: Refactoring Improvement
- **Commit Hash**: `df6a2a2`
- **Branch**: main
- **Date**: 2026-03-05
- **Author**: version-commit-agent

## Commit Messages

### Commit 1
```
Fix duplicate code block in renderer.py causing double render time

Removed duplicate image extraction and saving code block (lines 304-335)
that was causing each object to be rendered twice. This bug was causing
DLC jobs to take 2x expected time.

Changes:
- Deleted 33 lines of duplicate code in render_thumbnail_wo_bg()
- Reorganized imports (std lib first, then third party)
- Moved traceback import to module level (was imported inline twice)

Fixes: Double render time issue in render_thumbnail_wo_bg method
```

### Commit 2
```
Refactor: Use explicit Exception handling instead of bare except

Changed bare 'except:' to 'except Exception:' in three locations:
- Line 201: delete_prim error handling in prim validation
- Line 282: bbox2d_data extraction error handling
- Line 295: cleanup delete_prim error handling

This follows Python best practices (PEP 8) by avoiding bare except
clauses which can catch unexpected exceptions like SystemExit.
```

## Files Changed

| Commit | File | Changes |
|--------|------|---------|
| 8c1eb14 | `src/render_usd/core/renderer.py` | +5 lines, -38 lines |
| df6a2a2 | `src/render_usd/core/renderer.py` | +4 lines, -4 lines |

## Bug Description

The `render_thumbnail_wo_bg()` method in `renderer.py` contained a duplicate code block
at lines 304-335 that was identical to the code at lines 254-284. This caused:

1. Each object to be rendered and saved twice
2. DLC jobs taking 2x the expected time (16+ hours instead of ~8 hours)
3. Unnecessary CPU/GPU resource consumption

## Fix Details

The fix removed the duplicate code block (lines 304-335) which included:
- Duplicate `os.makedirs(save_dir, exist_ok=True)`
- Duplicate camera loop with RGBA extraction and alpha compositing
- Duplicate file saving logic with bbox2d handling
- Duplicate `delete_prim(show_prim_path)` call

Additional improvements (Commit 1):
- Reorganized imports to follow PEP 8 style (std lib first, then third party)
- Moved `traceback` import to module level (was previously imported inline in two places)

Additional improvements (Commit 2):
- Changed bare `except:` to `except Exception:` in three locations
- Follows Python best practices (PEP 8) to avoid catching unexpected exceptions like SystemExit

## Impact

- **Performance**: Rendering time reduced by ~50%
- **Resource Usage**: CPU/GPU usage normalized
- **Output**: No change in output (duplicate was overwriting the first save)

## Related Tasks

- Task #2: Investigate duplicate code block in renderer.py
- Task #6: Implement code fix for duplicate block
- Task #7: Design fix solution for duplicate code
