# Residual 532 Triage

## Problem

After four verified source-overwrite waves, `532` historical object-like non-ok assets still do not satisfy the strict four-view `ok;ok;ok;ok` thumbnail contract.

The goal of this triage is to decide whether another broad rerender wave is justified, or whether the remaining rows should be treated as category/asset-quality residuals.

## Current Counts

Input CSV:

`docs/tmp/final-source-verification-2026-05-09/current_object_non_ok_quality_after_residual.csv`

Final residual class counts:

- `suspicious`: `508`
- `blank`: `22`
- `tiny`: `2`
- Total: `532`

Top categories:

- `pillow`: `283`
- `pen`: `57`
- `book`: `32`
- `bottle`: `25`
- `cup`: `20`
- `cabinet`: `19`
- `toy`: `17`
- `picture`: `15`
- `plant`: `11`
- `shelf`: `10`

Dominant view patterns show partial-view failures rather than total render failure:

- `blank;ok;ok;blank`: `94`
- `ok;ok;blank;blank`: `86`
- `ok;ok;ok;blank`: `58`
- `blank;ok;ok;ok`: `39`
- `ok;ok;blank;ok`: `30`
- `blank;blank;blank;blank`: `22`

## Investigation

Three independent read-only investigations were run:

- Pillow residuals.
- Small-object residuals: `pen`, `book`, `cup`, `toy`, `picture`, `decoration`, `plate`, `plant`, `towel`.
- Remaining `blank`/`tiny` residuals.

### Pillow

Pillow is the largest residual group: `283/532`, all `suspicious`.

Pillow view patterns are dominated by one- or two-view failures:

- `blank;ok;ok;blank`: `85`
- `ok;ok;blank;blank`: `80`
- `ok;ok;ok;blank`: `36`
- `blank;ok;ok;ok`: `10`

No pillow rows appeared in the current residual bbox rerender analysis, so the latest bbox scan did not identify pillow as another bbox-fallback recovery group.

This looks like category/view-classifier behavior for flat or soft geometry: many rows have usable views, but at least one canonical view is edge-on, too small, or background-like.

### Small Objects

The main small-object residual group contains `174/532` rows across `pen`, `book`, `cup`, `toy`, `picture`, `decoration`, `plate`, `plant`, and `towel`.

Summary:

- `suspicious`: `158`
- `blank`: `14`
- `tiny`: `2`
- Exactly one bad view: `90`
- One or two bad views: `137`
- All blank: `14`

The dominant signal is partial-view failure, especially for thin, elongated, flat, or small objects. This is consistent with edge-on views and strict four-view classification rather than a new general camera bug.

### Blank And Tiny Residuals

All remaining `blank`/`tiny` cases are contained in `24` rows:

- `pen`: `6`
- `bottle`: `5`
- `cabinet`: `2`
- `cup`: `2`
- `decoration`: `2`
- `plant`: `2`
- `toy`: `2`
- `book`: `1`
- `couch`: `1`
- `picture`: `1`

Current residual bbox scan covered all `24` rows.

- `22/24` had no bbox fallback signal: `fallback_changed=false`, `diag_ratio=1.0`, `center_offset_ratio=0`.
- `2/24` were recommended by bbox scan.
- `cabinet/3399337a68a2bb41b4f4ebc20590fd94` was rerendered but remained `blank;blank;blank;blank`.
- `pen/5259a9e94e1c0a24de525763dc3e9c7c` improved only to `ok;ok;ok;tiny`, so it was not safe to copy back under the four-view `ok` rule.

## Decision

Do not launch another broad bbox rerender wave for the remaining `532` assets.

The known systematic bbox failure modes have already been harvested:

- Initial bbox-ratio recovery copied back `460` assets.
- Bottle center-offset recovery copied back `387` assets.
- Non-bottle center-offset recovery copied back `1,369` assets.
- Current residual bbox recovery copied back `616` assets.

The remaining set is mostly partial-view suspicious output from flat, thin, small, or category-specific geometry. This does not match the previous high-yield bbox/camera failure signatures.

## Recommended Next Actions

- Keep all `532` residuals excluded from automatic source overwrite unless a future render produces `ok;ok;ok;ok`.
- Treat `suspicious` residuals as downstream policy candidates, not renderer bug evidence.
- If downstream can tolerate category-specific rules, consider a separate classifier policy such as accepting pillow assets with at least two `ok` views.
- If manual audit budget exists, inspect only the `24` remaining `blank`/`tiny` rows first, especially the `14` all-blank small-object rows.
- Do not change the canonical `front/left/back/right` source thumbnails with best-view or diagonal-view salvage outputs unless that becomes an explicit new output contract.

## Result

The recovery work should be considered complete for the current strict four-view overwrite workflow. Remaining assets are residual quality/policy cases, not a safe high-yield rerender batch.
