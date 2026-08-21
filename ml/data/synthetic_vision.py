"""
TrackChain Synthetic Visual Defect Generation Engine (tc.v1 SOTA).
Generates photorealistic railway defects on normal track imagery or procedural canvases:
  - Class 0: missing_fastener (fastener removal, empty tie socket inpainting, rust residue)
  - Class 1: defective_clip (deformed, fractured, or displaced Pandrol elastic clips)
  - Class 2: crack (rolling-contact fatigue, branching cracks, transverse fissures on rail heads)
  - Class 3: obstruction (ballast rocks, metal tools, debris, wooden blocks on trackbed)

Outputs standard YOLO-format annotations [class_id, x_center, y_center, width, height].
"""

import math
import random
from typing import List, Dict, Tuple, Optional, Union, Any
from pathlib import Path
import numpy as np
import cv2


CLASS_MAPPING = {
    "missing_fastener": 0,
    "defective_clip": 1,
    "crack": 2,
    "obstruction": 3,
}

CLASS_NAMES = ["missing_fastener", "defective_clip", "crack", "obstruction"]


def sanitize_bbox(bbox: List[float]) -> Optional[List[float]]:
    """Sanitize and clamp YOLO bbox coordinates [x_center, y_center, width, height]."""
    if len(bbox) < 4:
        return None
    x, y, w, h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    if w <= 0.005 or h <= 0.005:
        return None
    x = max(0.01, min(0.99, x))
    y = max(0.01, min(0.99, y))
    w = max(0.01, min(1.0, w))
    h = max(0.01, min(1.0, h))

    half_w = w / 2.0
    half_h = h / 2.0
    x1 = max(0.0, x - half_w)
    y1 = max(0.0, y - half_h)
    x2 = min(1.0, x + half_w)
    y2 = min(1.0, y + half_h)

    new_w = x2 - x1
    new_h = y2 - y1
    if new_w <= 0.005 or new_h <= 0.005:
        return None

    new_x = (x1 + x2) / 2.0
    new_y = (y1 + y2) / 2.0
    return [round(new_x, 6), round(new_y, 6), round(new_w, 6), round(new_h, 6)]


class SyntheticRailDefectGenerator:
    """
    Photorealistic synthetic defect injection system for railway infrastructure.
    Uses normal track imagery as canvas to synthesize domain-accurate defect signatures.
    """

    def __init__(self, random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

    # -------------------------------------------------------------------------
    # 1. Crack Generation (Railhead surface defect - Class 2)
    # -------------------------------------------------------------------------
    def generate_crack_patch(
        self, width: int = 120, height: int = 120, crack_type: str = "branching"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate an alpha-masked crack patch with branching, irregular width,
        and realistic shadow/highlight edges.
        """
        patch = np.zeros((height, width, 3), dtype=np.uint8)
        alpha = np.zeros((height, width), dtype=np.float32)

        start_x = random.randint(int(width * 0.3), int(width * 0.7))
        start_y = random.randint(10, 25)
        curr_x, curr_y = start_x, start_y

        main_points = [(curr_x, curr_y)]
        angle = random.uniform(0.35 * math.pi, 0.65 * math.pi)  # downwards with jitter

        while curr_y < height - 15:
            step_len = random.randint(4, 9)
            angle += random.uniform(-0.4, 0.4)
            curr_x += int(step_len * math.cos(angle))
            curr_y += int(step_len * math.sin(angle))
            curr_x = max(5, min(width - 5, curr_x))
            curr_y = max(5, min(height - 5, curr_y))
            main_points.append((curr_x, curr_y))

        # Render main fissure with variable thickness and dark core
        for i in range(len(main_points) - 1):
            pt1 = main_points[i]
            pt2 = main_points[i + 1]
            thickness = random.choice([2, 3, 2, 1])
            darkness = random.randint(15, 45)
            cv2.line(patch, pt1, pt2, (darkness, darkness, darkness + 5), thickness)
            cv2.line(alpha, pt1, pt2, 1.0, thickness + 1)

            # Highlight edge (specular rail reflection next to fissure)
            offset_pt1 = (pt1[0] + 1, pt1[1])
            offset_pt2 = (pt2[0] + 1, pt2[1])
            cv2.line(patch, offset_pt1, offset_pt2, (180, 185, 190), 1)
            cv2.line(alpha, offset_pt1, offset_pt2, 0.4, 1)

        # Add secondary branching fissures
        if crack_type == "branching" and len(main_points) > 4:
            num_branches = random.randint(1, 3)
            branch_origins = random.sample(main_points[2:-2], min(num_branches, len(main_points) - 4))
            for bx, by in branch_origins:
                branch_angle = angle + random.choice([-1.0, 1.0]) * random.uniform(0.6, 1.2)
                bx_curr, by_curr = bx, by
                for _ in range(random.randint(3, 6)):
                    b_step = random.randint(3, 7)
                    bx_curr += int(b_step * math.cos(branch_angle))
                    by_curr += int(b_step * math.sin(branch_angle))
                    bx_curr = max(3, min(width - 3, bx_curr))
                    by_curr = max(3, min(height - 3, by_curr))
                    cv2.line(patch, (bx, by), (bx_curr, by_curr), (25, 25, 30), 1)
                    cv2.line(alpha, (bx, by), (bx_curr, by_curr), 0.8, 1)
                    bx, by = bx_curr, by

        # Smooth alpha mask for seamless blending
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0.5)
        return patch, alpha

    def inject_crack(
        self, image: np.ndarray, bbox_loc: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[np.ndarray, Optional[List[float]]]:
        """
        Inject synthetic crack onto rail head region.
        Returns modified image and normalized YOLO bbox.
        """
        h, w = image.shape[:2]
        img = image.copy()

        if bbox_loc is not None:
            x1, y1, x2, y2 = bbox_loc
            cw, ch = max(30, x2 - x1), max(30, y2 - y1)
        else:
            # Place crack along rail head area (typically vertical strip ~30% to 70% width)
            cw = random.randint(int(w * 0.08), int(w * 0.22))
            ch = random.randint(int(h * 0.12), int(h * 0.35))
            # Pick left or right rail zone
            rail_center_x = random.choice([int(w * 0.32), int(w * 0.68)])
            x1 = max(5, min(w - cw - 5, rail_center_x - cw // 2 + random.randint(-15, 15)))
            y1 = random.randint(int(h * 0.10), max(10, h - ch - int(h * 0.10)))
            x2, y2 = x1 + cw, y1 + ch

        crack_patch, alpha = self.generate_crack_patch(cw, ch)
        alpha_3d = np.expand_dims(alpha, axis=-1)

        roi = img[y1:y2, x1:x2].astype(np.float32)
        blended = roi * (1.0 - alpha_3d) + crack_patch.astype(np.float32) * alpha_3d
        img[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)

        # Compute YOLO normalized bbox [x_center, y_center, width, height]
        xc = (x1 + x2) / (2.0 * w)
        yc = (y1 + y2) / (2.0 * h)
        bw = (x2 - x1) / float(w)
        bh = (y2 - y1) / float(h)
        clean_box = sanitize_bbox([xc, yc, bw, bh])
        return img, clean_box

    # -------------------------------------------------------------------------
    # 2. Missing Fastener Generation (Class 0)
    # -------------------------------------------------------------------------
    def inject_missing_fastener(
        self, image: np.ndarray, bbox_loc: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[np.ndarray, Optional[List[float]]]:
        """
        Simulate missing Pandrol fastener / clip.
        Inpaints the clip area with empty tie socket, rust ring, and exposed baseplate/sleeper.
        """
        h, w = image.shape[:2]
        img = image.copy()

        if bbox_loc is not None:
            x1, y1, x2, y2 = bbox_loc
            fw, fh = max(25, x2 - x1), max(25, y2 - y1)
        else:
            # Fasteners sit adjacent to rails on sleepers
            fw = random.randint(int(w * 0.07), int(w * 0.14))
            fh = random.randint(int(h * 0.07), int(h * 0.14))
            # Typical fastener locations on baseplate (left/right of rail lines)
            x_band = random.choice([int(w * 0.22), int(w * 0.42), int(w * 0.58), int(w * 0.78)])
            x1 = max(5, min(w - fw - 5, x_band - fw // 2 + random.randint(-10, 10)))
            y1 = random.randint(int(h * 0.15), max(10, h - fh - int(h * 0.15)))
            x2, y2 = x1 + fw, y1 + fh

        roi = img[y1:y2, x1:x2]
        # Inpaint: replace clip with sleeper/baseplate texture + dark vacant socket cavity
        mask = np.zeros((fh, fw), dtype=np.uint8)
        cx, cy = fw // 2, fh // 2
        rx, ry = int(fw * 0.35), int(fh * 0.35)
        cv2.ellipse(mask, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)

        # Baseplate background color sampled from surrounding sleeper
        surrounding_color = np.median(roi, axis=(0, 1)).astype(np.float32)
        # Empty cavity texture (dark hole with rust ring)
        cavity = np.zeros((fh, fw, 3), dtype=np.uint8)
        cavity[:] = np.clip(surrounding_color * 0.85, 0, 255).astype(np.uint8)

        # Rust ring around hole
        rust_color = (random.randint(25, 45), random.randint(55, 85), random.randint(110, 150))
        cv2.ellipse(cavity, (cx, cy), (rx, ry), 0, 0, 360, rust_color, 3)
        # Dark void / bolt hole
        void_color = (random.randint(15, 30), random.randint(15, 30), random.randint(20, 35))
        cv2.ellipse(cavity, (cx, cy), (int(rx * 0.6), int(ry * 0.6)), 0, 0, 360, void_color, -1)

        # Add noise
        noise = np.random.normal(0, 12, (fh, fw, 3))
        cavity = np.clip(cavity.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # Blend cavity into ROI using smoothed mask
        mask_f = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (5, 5), 1.0)
        mask_3d = np.expand_dims(mask_f, axis=-1)
        blended = roi.astype(np.float32) * (1.0 - mask_3d) + cavity.astype(np.float32) * mask_3d
        img[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)

        xc = (x1 + x2) / (2.0 * w)
        yc = (y1 + y2) / (2.0 * h)
        bw = (x2 - x1) / float(w)
        bh = (y2 - y1) / float(h)
        clean_box = sanitize_bbox([xc, yc, bw, bh])
        return img, clean_box

    # -------------------------------------------------------------------------
    # 3. Defective / Damaged Clip Generation (Class 1)
    # -------------------------------------------------------------------------
    def inject_defective_clip(
        self, image: np.ndarray, bbox_loc: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[np.ndarray, Optional[List[float]]]:
        """
        Simulate deformed, cracked, broken, or misaligned Pandrol clip.
        Renders damaged clip geometry (sheared toe, fractured leg, heavy corrosion).
        """
        h, w = image.shape[:2]
        img = image.copy()

        if bbox_loc is not None:
            x1, y1, x2, y2 = bbox_loc
            cw, ch = max(30, x2 - x1), max(30, y2 - y1)
        else:
            cw = random.randint(int(w * 0.08), int(w * 0.15))
            ch = random.randint(int(h * 0.08), int(h * 0.15))
            x_band = random.choice([int(w * 0.24), int(w * 0.40), int(w * 0.60), int(w * 0.76)])
            x1 = max(5, min(w - cw - 5, x_band - cw // 2 + random.randint(-10, 10)))
            y1 = random.randint(int(h * 0.15), max(10, h - ch - int(h * 0.15)))
            x2, y2 = x1 + cw, y1 + ch

        roi = img[y1:y2, x1:x2]
        patch = np.zeros((ch, cw, 3), dtype=np.uint8)
        alpha = np.zeros((ch, cw), dtype=np.float32)

        # Draw deformed / severed e-clip loop
        clip_metal_color = (random.randint(60, 100), random.randint(65, 110), random.randint(80, 130))
        rust_color = (random.randint(20, 45), random.randint(45, 80), random.randint(120, 170))

        # Fractured loop arcs
        pts = np.array([
            [int(cw * 0.2), int(ch * 0.8)],
            [int(cw * 0.25), int(ch * 0.3)],
            [int(cw * 0.6), int(ch * 0.2)],
            [int(cw * 0.85), int(ch * 0.45)],
            [int(cw * 0.7), int(ch * 0.7)],
        ], np.int32)

        # Break the clip: omit middle section or deform angle
        break_idx = random.randint(1, 3)
        pts1 = pts[:break_idx]
        pts2 = pts[break_idx:]

        if len(pts1) >= 2:
            cv2.polylines(patch, [pts1], False, clip_metal_color, thickness=random.choice([4, 5]))
            cv2.polylines(alpha, [pts1], False, 0.95, thickness=random.choice([4, 5]))
        if len(pts2) >= 2:
            # Shift fractured piece (sheared/displaced)
            pts2_shifted = pts2 + np.array([random.randint(4, 10), random.randint(-6, 6)])
            cv2.polylines(patch, [pts2_shifted], False, rust_color, thickness=random.choice([4, 5]))
            cv2.polylines(alpha, [pts2_shifted], False, 0.95, thickness=random.choice([4, 5]))

        # Corrosion & fracture highlights
        noise = np.random.normal(0, 15, (ch, cw, 3))
        patch = np.clip(patch.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0.5)
        alpha_3d = np.expand_dims(alpha, axis=-1)

        blended = roi.astype(np.float32) * (1.0 - alpha_3d) + patch.astype(np.float32) * alpha_3d
        img[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)

        xc = (x1 + x2) / (2.0 * w)
        yc = (y1 + y2) / (2.0 * h)
        bw = (x2 - x1) / float(w)
        bh = (y2 - y1) / float(h)
        clean_box = sanitize_bbox([xc, yc, bw, bh])
        return img, clean_box

    # -------------------------------------------------------------------------
    # 4. Obstruction Generation (Class 3)
    # -------------------------------------------------------------------------
    def inject_obstruction(
        self, image: np.ndarray, bbox_loc: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[np.ndarray, Optional[List[float]]]:
        """
        Simulate track obstruction / foreign object (rock chunk, metal tool, timber piece, debris)
        with directional contact shadow.
        """
        h, w = image.shape[:2]
        img = image.copy()

        if bbox_loc is not None:
            x1, y1, x2, y2 = bbox_loc
            ow, oh = max(35, x2 - x1), max(35, y2 - y1)
        else:
            ow = random.randint(int(w * 0.08), int(w * 0.20))
            oh = random.randint(int(h * 0.08), int(h * 0.20))
            # Place in gauge area or on ballast trackbed
            x1 = random.randint(int(w * 0.20), max(5, w - ow - int(w * 0.20)))
            y1 = random.randint(int(h * 0.15), max(5, h - oh - int(h * 0.15)))
            x2, y2 = x1 + ow, y1 + oh

        roi = img[y1:y2, x1:x2]
        patch = np.zeros((oh, ow, 3), dtype=np.uint8)
        alpha = np.zeros((oh, ow), dtype=np.float32)

        obj_type = random.choice(["rock", "metal_tool", "debris"])

        if obj_type == "rock":
            # Polygonal rock lump
            num_pts = random.randint(6, 9)
            angles = np.sort(np.random.uniform(0, 2 * math.pi, num_pts))
            radii = np.random.uniform(min(ow, oh) * 0.3, min(ow, oh) * 0.45, num_pts)
            cx, cy = ow // 2, oh // 2
            poly_pts = np.array([
                [int(cx + r * math.cos(a)), int(cy + r * math.sin(a))]
                for a, r in zip(angles, radii)
            ], np.int32)
            rock_color = (random.randint(90, 140), random.randint(95, 145), random.randint(100, 150))
            cv2.fillPoly(patch, [poly_pts], rock_color)
            cv2.fillPoly(alpha, [poly_pts], 0.95)
        elif obj_type == "metal_tool":
            # Rectangular bar / wrench / spike
            pt1 = (int(ow * 0.15), int(oh * 0.8))
            pt2 = (int(ow * 0.85), int(oh * 0.2))
            cv2.line(patch, pt1, pt2, (60, 65, 75), thickness=random.randint(6, 12))
            cv2.line(alpha, pt1, pt2, 0.95, thickness=random.randint(6, 12))
            # Metallic reflection edge
            cv2.line(patch, (pt1[0], pt1[1] - 2), (pt2[0], pt2[1] - 2), (190, 195, 210), thickness=2)
        else:
            # Irregular debris piece
            cv2.ellipse(patch, (ow // 2, oh // 2), (int(ow * 0.4), int(oh * 0.25)), random.randint(0, 180), 0, 360, (50, 70, 90), -1)
            cv2.ellipse(alpha, (ow // 2, oh // 2), (int(ow * 0.4), int(oh * 0.25)), random.randint(0, 180), 0, 360, 0.90, -1)

        # Contact shadow (dark offset beneath object)
        shadow_mask = np.roll(alpha, shift=3, axis=0)
        shadow_patch = np.zeros_like(patch)

        noise = np.random.normal(0, 14, (oh, ow, 3))
        patch = np.clip(patch.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        alpha_clean = cv2.GaussianBlur(alpha, (3, 3), 0.5)
        alpha_3d = np.expand_dims(alpha_clean, axis=-1)

        blended = roi.astype(np.float32) * (1.0 - alpha_3d) + patch.astype(np.float32) * alpha_3d
        img[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)

        xc = (x1 + x2) / (2.0 * w)
        yc = (y1 + y2) / (2.0 * h)
        bw = (x2 - x1) / float(w)
        bh = (y2 - y1) / float(h)
        clean_box = sanitize_bbox([xc, yc, bw, bh])
        return img, clean_box

    # -------------------------------------------------------------------------
    # 5. Unified Multi-Defect Sample Generator
    # -------------------------------------------------------------------------
    def generate_synthetic_sample(
        self,
        base_image: np.ndarray,
        defect_types: Optional[List[str]] = None,
        max_defects: int = 2,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Inject one or more synthetic defects onto a base image and return annotated bboxes.
        """
        img = base_image.copy()
        bboxes: List[Dict[str, Any]] = []

        if defect_types is None:
            # Pick 1 to max_defects random defect types
            num_defects = random.randint(1, max_defects)
            chosen_types = [random.choice(CLASS_NAMES) for _ in range(num_defects)]
        else:
            chosen_types = defect_types

        for dt in chosen_types:
            clean_box = None
            if dt == "missing_fastener":
                img, clean_box = self.inject_missing_fastener(img)
                cls_id = 0
            elif dt == "defective_clip":
                img, clean_box = self.inject_defective_clip(img)
                cls_id = 1
            elif dt == "crack":
                img, clean_box = self.inject_crack(img)
                cls_id = 2
            elif dt == "obstruction":
                img, clean_box = self.inject_obstruction(img)
                cls_id = 3
            else:
                continue

            if clean_box is not None:
                bboxes.append({"class_id": cls_id, "bbox": clean_box})

        return img, bboxes
