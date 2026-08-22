# Training package exports (tc.v1 SOTA).

from ml.training.train_detector import train_yolo_detector
from ml.training.train_anomaly import train_patchcore
from ml.training.train_fault_classifier import train_fault_classifier
from ml.training.train_sequence_vae import train_sequence_vae

# Enhanced training scripts live in ml/scripts/ — import lazily to avoid heavy deps at package load
try:
    from ml.scripts.train_fault_classifier_enhanced import train_enhanced_bilstm
except ImportError:
    train_enhanced_bilstm = None

try:
    from ml.scripts.train_sequence_vae_enhanced import train_enhanced_vae
except ImportError:
    train_enhanced_vae = None

__all__ = [
    "train_yolo_detector",
    "train_patchcore",
    "train_fault_classifier",
    "train_sequence_vae",
    "train_enhanced_bilstm",
    "train_enhanced_vae",
]
