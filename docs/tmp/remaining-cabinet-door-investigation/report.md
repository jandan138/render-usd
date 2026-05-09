# Remaining Cabinet/Door Rerender Investigation

## Problem

After the bbox fallback fix and selected DLC rerender, 460 of 544 blank/tiny assets recovered to `ok`, but 84 assets remained non-ok. The residual set is concentrated in two categories:

- `cabinet`: 79
- `door`: 5

The goal of this investigation was to determine whether a small renderer change could safely recover these remaining assets without regressing the canonical four-view output contract.

## Investigation

Three independent reviews were run:

- Image-pattern review: inspected residual view classes, foreground metrics, and representative PNGs.
- USD/geometry review: compared failed cabinet/door assets against recovered cabinet controls.
- Renderer/camera review: traced bbox, camera distance, view angles, and output compositing code paths.

Key evidence:

- Residual asset classes: `tiny=58`, `blank=26`.
- Residual view classes: `tiny=62`, `blank=274`, `ok=0` across 336 baseline views.
- Many failures are sparse, flat, plank/frame-like assets rather than normal volumetric objects.
- Failed cabinets have much lower mesh complexity than recovered cabinets: representative failed cabinets often have tens to hundreds of points, while recovered controls can have thousands.
- Doors have no recovered examples in the selected set; side views naturally become edge-on for thin geometry.

## Experiments

Experiments were written only under `docs/tmp/remaining-cabinet-door-investigation/` and rendered to scratch output roots. No source USD or source dataset PNGs were modified.

Representative 7-asset baseline:

- `tiny=4`
- `blank=2`
- `ok=1` recovered cabinet control

Distance scale experiment, `distance_scale=0.5`, `elevation=35`:

- Did not improve the representative set overall.
- Some assets became more blank, which indicates the issue is not simply “camera too far”.

Double-sided experiment, `force_double_sided=True`:

- Matched baseline exactly on the representative set.
- This rejects “single-sided backface invisibility” as the primary residual root cause.

45-degree azimuth experiment on representatives:

- Converted some individual views to `ok`, but did not make any failed asset become fully four-view `ok`.

45-degree azimuth experiment on all 84 residual assets:

- Asset classes: `tiny=39`, `suspicious=28`, `blank=17`.
- View classes: `ok=29`, `tiny=42`, `blank=265`.
- No asset became all-four-views `ok`.

Combined 8-view status using baseline cardinal views plus 45-degree diagonal views:

- `has_ok_view`: 28
- `tiny_only_no_ok`: 47
- `all_blank`: 9

Classification output:

- `docs/tmp/remaining-cabinet-door-investigation/residual_84_classification.csv`

## Conclusion

The residual 84 assets are not solved by the simple renderer changes tested in this investigation:

- Reducing distance is not enough and can worsen framing.
- Forcing double-sided mesh rendering does not change results.
- Rotating views by 45 degrees gives some usable single views but does not satisfy the four-view contract.

The evidence supports treating these 84 as residual asset-quality/category-specific limitations, not as a remaining general bbox/camera bug. This is not proof that no renderer-side solution exists; it only rules out the tested simple variants as safe four-view fixes. Most residuals are thin cabinet/door assets where canonical four orthogonal views naturally include edge-on or visually empty views, and some appear to be sparse planks/frames rather than full objects.

## Decision

Do not change the production renderer for this residual set right now.

Recommended handling:

- Keep the 460 recovered `ok` rerender outputs as the safe bbox-fallback recovery set.
- Mark the remaining 84 as low-quality residuals.
- If downstream later accepts non-semantic thumbnails, add a separate opt-in best-view salvage mode. Do not overwrite `front/left/back/right` with diagonal or best-view outputs by default.

Consumption lists:

- Safe recovery candidates: `docs/tmp/bbox-rerender-selected-validation/recovered_ok_assets.csv`
- Residual low-quality assets: `docs/tmp/bbox-rerender-selected-validation/residual_low_quality_assets.csv`

## Residual Buckets

The 84 residuals should be consumed as three buckets:

- `has_ok_view` (`28`): at least one of the 8 tested angles produced an `ok` view. These are candidates only for a future best-view salvage artifact.
- `tiny_only_no_ok` (`47`): some foreground exists, but all tested views remain tiny or blank. These are poor salvage candidates without stronger post-processing or asset repair.
- `all_blank` (`9`): no view was classified as usable across baseline or 45-degree views. Some may contain tiny below-threshold foreground, but none produced a usable view. These should remain excluded unless USD/material issues are repaired upstream.

## Review Result

Two independent review agents agreed with the no-renderer-change decision. Both recommended marking the 84 residual cabinet/door assets as low-quality, with best-view salvage only as a future opt-in mode if semantic four-view consistency is no longer required.

## Files

- `experiment_assets.csv`: representative 7-asset experiment set.
- `non_ok_assets.csv`: all 84 residual assets.
- `residual_84_classification.csv`: final residual bucket classification.
- `../bbox-rerender-selected-validation/recovered_ok_assets.csv`: 460-asset safe recovery list.
- `../bbox-rerender-selected-validation/residual_low_quality_assets.csv`: 84-asset residual list.
- `analysis/`: representative experiment quality outputs.
- `analysis84/`: full 84-asset baseline and 45-degree quality outputs.
- `renders/`: representative experiment PNG outputs.
- `renders84/`: full 84-asset 45-degree experiment PNG outputs.
