# Train all models in sequence from configs.

from ml.training.train_fault_classifier import train_geometry_classifier
from ml.training.train_sequence_vae import train_vae
from ml.training.train_anomaly import train_patchcore
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("train_all")


def main():
    logger.info(">>> STEP 1: Training Bi-LSTM Fault Classifier")
    train_geometry_classifier(epochs=5)

    logger.info(">>> STEP 2: Training Sequence VAE on nominal geometry")
    train_vae(epochs=5)

    logger.info(">>> STEP 3: Fitting PatchCore Anomaly Detector")
    train_patchcore("ml/configs/anomaly.yaml")

    logger.info("All model training routines finished successfully.")


if __name__ == "__main__":
    main()
