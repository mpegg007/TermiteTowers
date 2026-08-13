# Water Meter Pipeline — Complete Calculation Logic

## Table of Contents
1. [Stage 1: decode_meter.py — Image Processing & Dial Detection](#stage-1-decode_meterpy--image-processing--dial-detection)
2. [Stage 2: decode_odo.py — Odometer Digit Recognition](#stage-2-decode_odopy--odometer-digit-recognition)
3. [Stage 3: calc_needle_readings.py — Combine Visual Digits with Needle Wraps](#stage-3-calc_needle_readingspy--combine-visual-digits-with-needle-wraps)
4. [Stage 4: auto_anchor_n00.py — Pos5 Drum-Digit Matching at n00 Frames](#stage-4-auto_anchor_n00py--pos5-drum-digit-matching-at-n00-frames)
5. [Stage 5: suggest_anchors.py — Manual Review Flagging](#stage-5-suggest_anchorspy--manual-review-flagging)
6. [Template Bank State](#template-bank-state)
7. [Identified Bugs](#identified-bugs)
8. [Proposed Fix Plan](#proposed-fix-plan)

---

## Stage 1: `decode_meter.py` — Image Processing & Dial Detection

### Image Quality Safeguards
- Skips files modified less than **30 seconds** ago (still being written by capture script).
- **No brightness threshold** — processes all images regardless of quality.

### Hub Detection (`detect_hub_and_dial` in `common.py`)
1. Extract red pixels via HSV thresholding (`RED_LOWER_1/2`, `RED_UPPER_1/2` — ranges [0-10] and [170-180]).
2. Apply morphological closing (5×5 elliptical kernel) to red mask.
3. Run **distance transform** on red mask — maximum distance point = `hub_x, hub_y` (dial center).
4. `hub_r` = distance value at the hub point (approximate radius of the central cross).

### Dial Radius Detection
5. Scan the horizon row (row `hub_y`) for bright pixels at `BRIGHT_THRESH=200`.
6. Find the bright run containing `hub_x` — this is the main dial face.
7. Outside the main dial face, find bright rectangular boxes of width 10-120px — these are the segment boundary boxes.
   - Outermost left = `left_edge`, outermost right = `right_edge`.
8. `dial_r = hub_x - left_edge` — the dial radius.

### Vertical Extent
9. Scan columns within ±`dial_r` of `hub_x` for vertical extent of `BRIGHT_THRESH` pixels.
10. `dial_ry = max_bright_vertical_extent / 2`.

### Marker Detection (the physical red arrow)
11. Exclude a circular area of radius `3 * hub_r` around the hub from the red mask.
12. Run connected components on the excluded red pixels.
13. Find the best candidate to the **left** of hub_x with area > 500px.
14. `marker_cx, marker_cy` = centroid of this blob.

### Needle Angle
15. Collect red pixels that are within the dial radius but **outside** the inner ellipse (`inner_rx, inner_ry`) — this is the needle zone.
16. Compute the centroid of the needle-zone pixels.
17. `needle_deg = atan2(needle_zones - hub_y, needle_zones - hub_x)` — angle of the red needle relative to hub.
18. `npos = ((needle_deg + 90) % 360) / 360 * 100` — normalized to 0-99.

### Odometer Crop (`crop_odometer`)
19. Crop the odometer region from the full-resolution image based on predefined offsets from the hub.
20. Save to `proc/YYYY-MM-DD/odo_{timestamp}_n{npos}.jpg`.
21. Write `odo_crop_file` (relative path), all geometry, and image stats (`brightness`, `contrast`, `entropy`) to DB.

### What `decode_meter.py` does NOT do
- **No cross-frame logic.** Each image is processed independently.
- **No revolution counting.** Needle wrap detection is handled later by `calc_needle_readings.py`.
- **No digit reading.** Odometer digit recognition is handled by `decode_odo.py`.

### DB columns written by `decode_meter.py`
`image_name`, `capture_ts`, `processed_ts`, `status`, `hub_x`, `hub_y`, `hub_r`, `dial_r`, `dial_ry`, `left_edge`, `right_edge`, `inner_rx`, `inner_ry`, `nz_pix`, `marker_cx`, `marker_cy`, `marker_extent`, `needle_deg`, `npos`, `horizon_deg`, `hrow_mean`, `hrow_std`, `img_brightness`, `img_contrast`, `odo_x1`, `odo_y1`, `odo_w`, `odo_h`, `odo_brightness`, `odo_contrast`, `img_width`, `img_height`, `odo_crop_file`, `odo_width`, `odo_height`, `odo_mean`, `odo_std`, `odo_sobel_mean`, `odo_sobel_std`, `odo_hist_entropy`, `clean_read`, `clean_archive`

---

## Stage 2: `decode_odo.py` — Odometer Digit Recognition

For each odometer crop image in `proc/`:

### Slot Extraction
1. Scale predefined pixel slots by image width:  
   `DIGIT_SLOTS = [(24,78), (119,173), (197,251), (289,343), (368,422), (432,508)]`  
   divided by `REFERENCE_CROP_W=558`.
2. Refine slot boundaries using Sobel edge projection (for pixel-drift tolerance).
3. Compute a dynamic confidence threshold from image statistics (entropy, contrast).

### pos0-4 (Static White Digits — Hundreds to Ten-Thousands)
4. Ensemble template matching against per-position template banks. Three paths:
   - Raw grayscale
   - CLAHE + Otsu threshold
   - Adaptive binarization
5. Each position's template bank contains **only the digits that have been extracted** so far.

    **Current template bank state:**

    | Position | Templates Present | Can Read |
    |---|---|---|
    | pos0 (ten-thousands) | digit 0 only | Only 0 |
    | pos1 (thousands) | digit 3 only | Only 3 |
    | pos2 (hundreds) | digit 5 only | Only 5 |
    | pos3 (tens) | digit 3 only | Only 3 |
    | pos4 (ones) | digits 2,3,4,5,6,7,8,9 | Missing 0,1 |
    | pos5 (tenths/drum) | 64 templates (digits 0-8 × 7 npos angles) | Missing digit 9 at n00 |

6. If the per-digit bank is empty, falls back to composite template matching (which can only answer "match/no-match", not "which digit?").

### pos5 (Rotating Drum Digit)
7. npos-constrained matching: only matches templates at the same npos ±5.
8. If template matching fails, uses `known_pos5` (needle-tracked digit from lag filter).

### Monotonicity Batch Mode (chronological order)
9. `running_reading` starts at 0, only updated upward from **non-n00 frames** with confidence ≥ 0.70.
10. **Ceiling check**: If reading exceeds the next manual anchor → clamp to that anchor value, zero all 6 position confidences.
11. **Floor check** (modified today): If reading falls below `running_reading - 0.01` → only replace positions that actually matched wrong.  
    **Exception for pos5**: In n00 zone (npos 98-2) with pos5_conf > 0.80, **trust the template's drum digit** even if it means reading higher than the floor.
12. Steps 9-11 are the **only** way digits can change over time, given the template bank gaps.

### Output
Writes `digits` (6-char string, e.g. `"035417"`), `odo_reading` (bucket 1), `odo_confidence` (mean of per-position confidences), and `pos_confs`/`pos_digits` into notes JSON.  
**Does NOT modify** `odo_needle` or `odo_published`.

---

## Stage 3: `calc_needle_readings.py` — Combine Visual Digits with Needle Wraps

### Input
All rows ordered by `capture_ts` ascending. No status filtering — processes all rows.

### Parsing (per row)
```python
visual_int      = int(digits[:5])  # e.g. "03541" → 3541
visual_tenths   = int(digits[5])   # e.g. "7" → 7
odo_manual      = row.odo_manual if not None
```

### Forward Processing Loop (chronological, lines 87-151)
1. **Deduplication**: If npos == last_npos, skip (emit same reading).
2. **Needle wrap detection**: If `last_npos > 85` AND `npos < 10` AND >5 minutes since last wrap:  
   `last_visual_tenths += 1`. If tenths overflows past 9 → `last_visual_int += 1`.
3. **False drop detection**: If npos drops >50 but does not qualify as a real wrap: log and ignore.
4. **Visual reset**: If this row has `visual_int != None` AND `visual_int != 3532` (poison value):  
   `last_visual_int = visual_int` and `last_visual_tenths = visual_tenths`.  
   **All accumulated needle wraps between visual resets are discarded** — the visual reading is absolute.
5. **Manual fallback**: If no visual digits but row has `odo_manual`: use that integer value.
6. **Emit reading**: `reading = last_visual_int + last_visual_tenths/10 + npos/1000`.

### Output
Writes `odo_needle = reading` and `odo_published = reading` (overwrites any prior values in both fields).

### Key Behavior
When `digits` is "035415" (tenths=5) and 30 minutes later `digits` becomes "035417" (tenths=7), the system jumps instantly by 0.2 m³ at the visual reset — intermediate needle wraps that should have incremented tenths from 5→6→7 are lost because the visual reset discards them.

---

## Stage 4: `auto_anchor_n00.py` — Pos5 Drum-Digit Matching at n00 Frames

1. Selects only odometer crops with npos ∈ {98, 99, 0, 1, 2} (drum fully settled).
2. Matches pos5 slot against n00-specific pos5 templates using 3-path ensemble (raw + adaptive binarized).
3. Writes match result to DB notes under `n00_anchor` key: `{"pos5_digit": X, "pos5_confidence": Y, "pos5_gap": Z}`.
4. **Not used by `calc_needle_readings.py`** — currently diagnostic only.

---

## Stage 5: `suggest_anchors.py` — Manual Review Flagging

1. Finds n00 anchor rows where the template-matched pos5 digit differs from the needle-tracked ones digit by >1.
2. Only flags rows whose **source image still exists on disk** (checked across `keepers/`, `scanned/`, `pending/`).
3. Only considers the **last 7 days** (older images may be archived).
4. Writes `"needs_review": "pos5_mismatch:dX→Y"` to notes.

---

## Template Bank State

Templates live in `~/pictures/water_meter/templates/`. They are extracted by:
- `extract_n00_seeds.py` — for pos5 drum templates at n00/n10/n20/n30/n70/n80/n90 positions
- `update_templates.py` — for static digit templates (pos0-4), only from **manually verified** rows (`odo_confidence >= 0.80`)

### Current counts as of 2026-08-05:

| Position | Files | Can Distinguish |
|---|---|---|
| pos0 | 1 digit (0) | Only reads "0" |
| pos1 | 1 digit (3) | Only reads "3" |
| pos2 | 1 digit (5) | Only reads "5" |
| pos3 | 1 digit (3) | Only reads "3" |
| pos4 | 8 digits (2-9) | Missing 0, 1 |
| pos5 | 64 (digits 0-8 × npos angles) | Missing digit 9 at n00 |

### How templates get created
1. User manually corrects a reading in the webapp (`odo_manual` set, confidence→1.0)
2. `update_templates.py --refresh` reads those rows, extracts digit boxes from their odo crops
3. Saves new `posN_digitD.png` files to the template directory
4. `decode_odo.py` picks them up on next run

**There is currently no automated template training from `odo_published` values.**

---

## Identified Bugs

### Bug 1: pos0-3 Template Bank Gaps
`decode_odo.py` can only visually read digits 0, 3, 5, 3 at positions 0-3 because those are the only templates ever extracted. Digits 1, 4, 7 can only enter the `digits` field through the monotonicity floor (Stage 2, steps 9-11), which requires a preceding reliable read to push the floor upward.

**Impact**: `digits` is stuck at `0353XX` for all frames. The pos5 drum digit can change (via the n00 exception), but the tens-to-thousands digits never update from template matching alone.

### Bug 2: Visual Reset Discards Needle Wraps
When `calc_needle_readings.py` encounters a new `digits` value (Stage 3, step 4), it resets `last_visual_int` and `last_visual_tenths` to the visual values, discarding all needle wraps accumulated since the last visual frame. This creates instantaneous jumps of 0.2+ m³ when `digits` updates, while the tenths digit remains frozen between updates.

**Impact**: `odo_published` lags behind reality because visual updates are infrequent (template-limited), and needle wraps between updates are thrown away.

### Bug 3: `odo_published` = Visual `digits` + npos
The formula in Stage 3 step 6 makes `odo_published` directly dependent on `digits` quality. When `digits` is stale (which it almost always is due to Bug 1), `odo_published` is also stale.

### Bug 4: n00 Pos5 Anchor Data Unused
`auto_anchor_n00.py` stores template-matched pos5 digits with confidences up to 0.98, but `calc_needle_readings.py` ignores this data. These anchors could serve as ground-truth validation points for both the needle counter and the visual digits.

---

## Proposed Fix Plan

### Fix A: Fill pos0-3 Template Bank Using `odo_published` as Ground Truth
Extract digit boxes from frames where `odo_published` is reliable (after the physics fix: 1 wrap = 0.1 m³, real-wrap-only detection, 5-min rate limit). Save as `posN_digitD.png` templates. This gives `decode_odo.py` the ability to independently read all 6 digits.

### Fix B: Remove Visual Reset — Use Visual Digits Only for Bootstrap
`calc_needle_readings.py` should use visual `digits` values as an **initial bootstrap** for the integer part, but track tenths via **needle wraps only**. Visual reads of pos5 should cross-validate but not replace the tracked tenths value.

### Fix C: Trust High-Confidence n00 Pos5 Anchors
When `auto_anchor_n00.py` produces a pos5 match with confidence > 0.90 and a discrimination gap > 0.02, it should be treated as ground truth for the drum digit. When 2+ consecutive n00 anchors agree on a digit different from the tracked ones digit, snap the tracker.

### Fix D: Stop Overwriting `digits` Field
`digits` should remain as-written by `decode_odo.py` (visual odometer recognition). `calc_needle_readings.py` should NOT reconstruct a digits string from its computed reading — it should only update `odo_needle` and `odo_published`.