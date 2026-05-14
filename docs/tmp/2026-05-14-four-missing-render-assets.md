# Four Missing Render Assets Investigation 2026-05-14

## Problem

Four final `GRScenes_assets` entries were reported as missing rendered thumbnails:

- `cabinet/b98d6ccbeb75dfdeb60e27649a5b055a`
- `other/d41d8cd98f00b204e9800998ecf8427e`
- `person/351316cbb083f9f4df0cccd60cbfa848`
- `person/d41d8cd98f00b204e9800998ecf8427e`

The goal was to determine whether these are render failures, DLC/copy-back misses, or upstream dataset artifacts.

## Investigation

The current final dataset root checked was:

`/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets`

Each reported asset directory exists, but each directory contains only one annotation JSON and no renderable USD or PNG outputs:

| asset | png count | usd count | json count | total files |
| --- | ---: | ---: | ---: | ---: |
| `cabinet/b98d6ccbeb75dfdeb60e27649a5b055a` | 0 | 0 | 1 | 1 |
| `other/d41d8cd98f00b204e9800998ecf8427e` | 0 | 0 | 1 | 1 |
| `person/351316cbb083f9f4df0cccd60cbfa848` | 0 | 0 | 1 | 1 |
| `person/d41d8cd98f00b204e9800998ecf8427e` | 0 | 0 | 1 | 1 |

Category-level spot checks show these are the only annotation-only entries in their categories:

| category | dirs | dirs with 4 PNGs | annotation-only dirs |
| --- | ---: | ---: | ---: |
| `cabinet` | 1223 | 1222 | 1 |
| `other` | 11177 | 11176 | 1 |
| `person` | 119 | 117 | 2 |

The upstream workspace recorded in `workspace_manifest.json` is:

`/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_20260421_103046`

The same four entries were already annotation-only in that upstream workspace. This means the current parallel workspace inherited empty asset shells; it did not create this missing-render state during the latest render recovery passes.

The `render_custom` CLI only discovers assets with the structure:

`Category/UID/usd/UID.usd`

For these four entries, the `usd/` directory and `UID.usd` file do not exist, so the renderer's scanner cannot enqueue them for rendering.

Additional evidence:

- The four IDs do not appear in the category dedup/apply mapping records.
- `other` and `person` category apply/audit completed, but these entries were not part of the mapped replacement set.
- `cabinet` in the current parallel workspace has certification outputs but no current `02_apply`/`03_audit`; however the same `cabinet/b98...` entry was already annotation-only in the upstream source workspace.
- `d41d8cd98f00b204e9800998ecf8427e` is the MD5 hash of the empty string, which strongly indicates an upstream empty-ID placeholder. It appears as an annotation-only UID in multiple backup locations as well.

## Per-Asset Diagnosis

### `cabinet/b98d6ccbeb75dfdeb60e27649a5b055a`

Observed files:

- Present: `b98d6ccbeb75dfdeb60e27649a5b055a_annotation.json`
- Missing: `front.png`, `left.png`, `back.png`, `right.png`
- Missing: `usd/b98d6ccbeb75dfdeb60e27649a5b055a.usd`

Annotation summary:

- `category`: `cabinet`
- `asset_type`: `articulation`
- `usd_size`: `0.0021810531616210938`
- `description`, `material`, `dimensions`, `mass`: empty strings

Specific problem:

This is a metadata-only cabinet entry. The directory has no USD payload and no existing thumbnail PNGs. It was already annotation-only in the upstream `test0_transitive_apply_20260421_103046` workspace, so the current render pipeline did not lose these images. The renderer skipped it because the required `usd/<uid>.usd` file does not exist.

Recommended action:

Exclude this row from render-missing retry lists unless the original cabinet USD can be restored.

### `other/d41d8cd98f00b204e9800998ecf8427e`

Observed files:

- Present: `d41d8cd98f00b204e9800998ecf8427e_annotation.json`
- Missing: `front.png`, `left.png`, `back.png`, `right.png`
- Missing: `usd/d41d8cd98f00b204e9800998ecf8427e.usd`

Annotation summary:

- `category`: `other`
- `asset_type`: `rigid`
- `usd_size`: `0.0014247894287109375`
- `description`, `material`, `dimensions`, `mass`: empty strings

Specific problem:

This is an empty-ID placeholder shell. The UID `d41d8cd98f00b204e9800998ecf8427e` is the MD5 hash of an empty string, and the directory contains only annotation metadata. It has no renderable source asset. It was also present as an annotation-only entry in upstream and backup locations.

Recommended action:

Treat it as invalid upstream metadata and exclude it from render completeness checks, unless the real non-empty source UID can be recovered.

### `person/351316cbb083f9f4df0cccd60cbfa848`

Observed files:

- Present: `351316cbb083f9f4df0cccd60cbfa848_annotation.json`
- Missing: `front.png`, `left.png`, `back.png`, `right.png`
- Missing: `usd/351316cbb083f9f4df0cccd60cbfa848.usd`

Annotation summary:

- `category`: `person`
- `asset_type`: `rigid`
- `usd_size`: `0.0013332366943359375`
- `description`, `material`, `dimensions`, `mass`: empty strings

Specific problem:

This is a metadata-only person entry. It was not part of the person dedup/apply replacement records, and it has no `usd/` directory. The person category has two annotation-only entries in the final dataset; this is one of them.

Recommended action:

Exclude it from render-missing retry lists unless the original person USD can be restored.

### `person/d41d8cd98f00b204e9800998ecf8427e`

Observed files:

- Present: `d41d8cd98f00b204e9800998ecf8427e_annotation.json`
- Missing: `front.png`, `left.png`, `back.png`, `right.png`
- Missing: `usd/d41d8cd98f00b204e9800998ecf8427e.usd`

Annotation summary:

- `category`: `person`
- `asset_type`: `articulation`
- `usd_size`: `0.001537322998046875`
- `description`, `material`, `dimensions`, `mass`: empty strings

Specific problem:

This is another empty-ID placeholder shell. Like the `other/d41...` row, its UID is the MD5 hash of an empty string. The directory has annotation metadata only and no renderable USD. It is one of the two annotation-only `person` entries in the final dataset.

Recommended action:

Treat it as invalid upstream metadata and exclude it from render completeness checks, unless the real non-empty source UID can be recovered.

## Solution

No renderer fix was applied. These four entries are not normal failed renders; they are invalid or incomplete asset records with metadata only.

Recommended handling:

- Exclude these four entries from "missing render" retry queues unless their original USD payloads are restored.
- If they must be kept, rehydrate each asset from the original source package so that `Category/UID/usd/UID.usd` exists, then rerun `render_custom`.
- Add an upstream integrity check that reports any `GRScenes_assets/<category>/<uid>` directory missing both `usd/<uid>.usd` and the four required PNGs.

## Results

Root cause: upstream dataset assembly retained four annotation-only asset shells. The renderer did not generate thumbnails because there was no renderable USD file for any of the four assets.

Impact:

- `cabinet/b98d6ccbeb75dfdeb60e27649a5b055a`: one annotation-only cabinet shell.
- `other/d41d8cd98f00b204e9800998ecf8427e`: empty-ID placeholder shell.
- `person/351316cbb083f9f4df0cccd60cbfa848`: one annotation-only person shell.
- `person/d41d8cd98f00b204e9800998ecf8427e`: empty-ID placeholder shell.
