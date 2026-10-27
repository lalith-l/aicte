"""Degradation levels (L0-L3) using Augraphy and OpenCV.

L0: Pristine born-digital (no degradation)
L1: High-quality office scanner (slight skew <1 deg, subtle brightness jitter)
L2: Field photocopy / mobile capture (moderate noise, paper texture, subtle bleedthrough)
L3: Degraded legacy scan (folds, dust, low contrast, heavy skew)

All generated documents are synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image
import io

try:
    from augraphy import (
        AugraphyPipeline,
        SubtleNoise,
        PageBorder,
        DirtyRollers,
        BleedThrough,
        Brightness,
        LightingGradient,
        BadPhotoCopy,
    )
    HAVE_AUGRAPHY = True
except ImportError:
    HAVE_AUGRAPHY = False


def _get_pipeline_l1():
    if not HAVE_AUGRAPHY:
        return None
    return AugraphyPipeline(
        ink_phase=[Brightness(range=(0.95, 1.05))],
        paper_phase=[SubtleNoise(range_range=(1, 5))],
        post_phase=[],
    )


def _get_pipeline_l2():
    if not HAVE_AUGRAPHY:
        return None
    return AugraphyPipeline(
        ink_phase=[
            Brightness(range=(0.85, 1.15)),
        ],
        paper_phase=[
            SubtleNoise(range_range=(5, 15)),
            PageBorder(side="random", width_range=(2, 6)),
        ],
        post_phase=[
            LightingGradient(light_position=None, direction=None, max_brightness=220, min_brightness=120),
        ],
    )


def _get_pipeline_l3():
    if not HAVE_AUGRAPHY:
        return None
    return AugraphyPipeline(
        ink_phase=[
            BleedThrough(intensity_range=(0.1, 0.3)),
            BadPhotoCopy(noise_iteration_range=(1, 3)),
        ],
        paper_phase=[
            DirtyRollers(line_width_range=(2, 8)),
            SubtleNoise(range_range=(10, 25)),
            PageBorder(side="all", width_range=(4, 12)),
        ],
        post_phase=[],
    )


def degrade_image(img_pil: Image.Image, level: int = 0) -> Image.Image:
    """Apply degradation level 0-3 to PIL Image."""
    if level == 0 or not HAVE_AUGRAPHY:
        return img_pil

    img_np = np.array(img_pil)
    # Ensure RGB
    if len(img_np.shape) == 2:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
    elif img_np.shape[2] == 4:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
    else:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    if level == 1:
        pipe = _get_pipeline_l1()
    elif level == 2:
        pipe = _get_pipeline_l2()
    else:
        pipe = _get_pipeline_l3()

    if pipe:
        try:
            degraded_np = pipe(img_np)
            return Image.fromarray(cv2.cvtColor(degraded_np, cv2.COLOR_BGR2RGB))
        except Exception:
            return img_pil
    return img_pil
