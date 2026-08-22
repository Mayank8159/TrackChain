import os
import cv2
import numpy as np
import onnxruntime as ort
from typing import List, Dict

# SOTA ONNX YOLOv8 loader for TrackChain cloud deployments

_session = None
_loaded = False
_classes = [
    "rail_crack", "rail_missing_fastener", "rail_broken",
    "rail_spalling", "rail_squat", "rail_buckling",
    "sleeper_cracked", "sleeper_broken", "sleeper_missing",
    "ballast_fouled", "ballast_pumping", "vegetation_overgrowth"
]

def load_onnx_model():
    global _session, _loaded
    if _loaded:
        return
        
    model_paths = [
        "artifacts/exports/yolov8n_rail_best.onnx",
        "../artifacts/exports/yolov8n_rail_best.onnx",
        "yolov8n_rail_best.onnx",
    ]
    
    found = None
    for p in model_paths:
        if os.path.exists(p):
            found = p
            break
            
    if not found:
        print(f"[ONNX] Could not find YOLOv8 ONNX model in {model_paths}")
        _loaded = False
        return
        
    try:
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Check providers, fallback to CPU
        providers = ['CPUExecutionProvider']
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            providers = ['CUDAExecutionProvider'] + providers
            
        _session = ort.InferenceSession(found, options, providers=providers)
        _loaded = True
        print(f"[ONNX] YOLO loaded from {found} using {providers[0]}")
    except Exception as e:
        print(f"[ONNX] Failed to load YOLO: {e}")
        _loaded = False


def preprocess(img: np.ndarray) -> np.ndarray:
    """Preprocess image for YOLOv8 (640x640, RGB, normalize)"""
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Pad to square
    h, w = img_rgb.shape[:2]
    max_dim = max(h, w)
    pad_h = (max_dim - h) // 2
    pad_w = (max_dim - w) // 2
    
    padded = cv2.copyMakeBorder(
        img_rgb, 
        pad_h, max_dim - h - pad_h,
        pad_w, max_dim - w - pad_w,
        cv2.BORDER_CONSTANT, value=(114, 114, 114)
    )
    
    resized = cv2.resize(padded, (640, 640))
    blob = resized.astype(np.float32) / 255.0
    blob = blob.transpose(2, 0, 1) # HWC to CHW
    blob = np.expand_dims(blob, axis=0) # Add batch dim
    
    return blob, (w, h), (pad_w, pad_h), max_dim

def postprocess(output: np.ndarray, orig_shape: tuple, pad_info: tuple, max_dim: int, conf_thresh: float = 0.25) -> List[Dict]:
    """Postprocess YOLOv8 ONNX outputs into bounding boxes"""
    # YOLOv8 output is [batch, 4+num_classes, 8400]
    preds = output[0]
    preds = preds.T # Now [8400, 4+num_classes]
    
    boxes = []
    w_orig, h_orig = orig_shape
    pad_w, pad_h = pad_info
    
    for row in preds:
        box = row[:4]
        scores = row[4:]
        class_id = np.argmax(scores)
        conf = scores[class_id]
        
        if conf > conf_thresh:
            cx, cy, w, h = box
            
            # Map 640x640 coords back to padded image
            cx = cx / 640.0 * max_dim
            cy = cy / 640.0 * max_dim
            w = w / 640.0 * max_dim
            h = h / 640.0 * max_dim
            
            # Remove padding
            cx -= pad_w
            cy -= pad_h
            
            # Convert to xmin, ymin, xmax, ymax
            xmin = cx - w/2
            ymin = cy - h/2
            xmax = cx + w/2
            ymax = cy + h/2
            
            # Clip to bounds
            xmin = max(0, min(xmin, w_orig))
            xmax = max(0, min(xmax, w_orig))
            ymin = max(0, min(ymin, h_orig))
            ymax = max(0, min(ymax, h_orig))
            
            class_name = _classes[class_id] if class_id < len(_classes) else str(class_id)
            
            boxes.append({
                "class": class_name,
                "confidence": round(float(conf), 4),
                "xmin": round(float(xmin), 2),
                "ymin": round(float(ymin), 2),
                "xmax": round(float(xmax), 2),
                "ymax": round(float(ymax), 2),
            })
            
    # NMS (simplified, OpenCV provides NMSBoxes)
    if not boxes:
        return []
        
    cv_boxes = [[b['xmin'], b['ymin'], b['xmax']-b['xmin'], b['ymax']-b['ymin']] for b in boxes]
    cv_scores = [b['confidence'] for b in boxes]
    indices = cv2.dnn.NMSBoxes(cv_boxes, cv_scores, conf_thresh, 0.45)
    
    final_boxes = []
    if len(indices) > 0:
        for i in indices.flatten():
            final_boxes.append(boxes[i])
            
    return final_boxes


def infer_yolo(img: np.ndarray, conf_thresh: float = 0.25) -> List[Dict]:
    """Run ONNX inference on the image"""
    global _session, _loaded
    
    if not _loaded:
        load_onnx_model()
        if not _loaded:
            return []
            
    try:
        blob, orig_shape, pad_info, max_dim = preprocess(img)
        
        input_name = _session.get_inputs()[0].name
        output_name = _session.get_outputs()[0].name
        
        outputs = _session.run([output_name], {input_name: blob})
        
        boxes = postprocess(outputs[0], orig_shape, pad_info, max_dim, conf_thresh)
        return boxes
    except Exception as e:
        print(f"[ONNX] Inference failed: {e}")
        return []
