# Threshold detector on EN 13848 & RDSO features for deterministic geometry fault alarms (tc.v1 SOTA).

from typing import List, Dict, Optional, Union, Any
from pathlib import Path
import numpy as np
import yaml
import pandas as pd

from ml.core.schema import DefectClass, CalibratedSignal, SignalType
from ml.core.registry import register_model, ModelRegistry
from ml.core.chainage import ChainageResampler
from ml.features.en13848 import EN13848PhysicsCalculator


@register_model("physics_detector")
class EN13848PhysicsThresholdDetector:
    """
    Deterministic safety threshold detector enforcing RDSO Broad Gauge (1676mm)
    and European EN 13848 track geometry limits (Immediate Action Limits & Alert Limits).
    
    Converts physical exceedance units (mm) into normalized probabilistic [0.0, 1.0] scores:
        Score = min(1.0, Measured_Value / (2.0 * Limit))
    Where:
        Measured = 0.0mm -> Score = 0.0
        Measured = Limit -> Score = 0.50 (Triggers operating threshold)
        Measured = 2x Limit -> Score = 1.0 (Critical severe exceedance)
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        nominal_gauge_mm: float = 1676.0,
        twist_limit_mm: float = 4.0,           # RDSO 3m Twist IAL (4mm)
        versine_limit_mm: float = 6.0,         # RDSO 10m Versine IAL (6mm)
        unevenness_limit_mm: float = 6.0,      # RDSO 10m Longitudinal Level IAL (6mm)
        gauge_limit_mm: float = 6.0,           # RDSO Gauge Variation (+6mm / -3mm)
        cross_level_limit_mm: float = 20.0,    # Cross-Level Cant limit (20mm)
        operating_threshold: float = 0.50,
    ):
        self.nominal_gauge = nominal_gauge_mm
        self.operating_threshold = operating_threshold
        self.resampler = ChainageResampler(step_size_m=0.25)
        self.calculator = EN13848PhysicsCalculator(nominal_gauge_mm=nominal_gauge_mm)

        self.limits = {
            "twist_3m": float(twist_limit_mm),
            "versine_10m": float(versine_limit_mm),
            "unevenness_10m": float(unevenness_limit_mm),
            "gauge_dev": float(gauge_limit_mm),
            "cross_level": float(cross_level_limit_mm),
        }

        # Override with config file if provided or available in configs/
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[Union[str, Path]] = None):
        cfg_file = None
        if config_path:
            p = Path(config_path)
            if p.exists():
                cfg_file = p
        else:
            default_p = ModelRegistry.ROOT / "ml" / "configs" / "physics_detector.yaml"
            if default_p.exists():
                cfg_file = default_p

        if cfg_file and cfg_file.exists():
            with open(cfg_file, "r") as f:
                data = yaml.safe_load(f) or {}
            std = data.get("standards", {}).get("rdso_broad_gauge_1676", {})
            lim = std.get("limits_mm", {})
            if "nominal_gauge_mm" in std:
                self.nominal_gauge = float(std["nominal_gauge_mm"])
                self.calculator.nominal_gauge = self.nominal_gauge
            if "twist_3m_mm" in lim:
                self.limits["twist_3m"] = float(lim["twist_3m_mm"])
            if "versine_10m_mm" in lim:
                self.limits["versine_10m"] = float(lim["versine_10m_mm"])
            if "unevenness_10m_mm" in lim:
                self.limits["unevenness_10m"] = float(lim["unevenness_10m_mm"])
            if "gauge_variation_mm" in lim:
                self.limits["gauge_dev"] = float(lim["gauge_variation_mm"])
            if "cross_level_mm" in lim:
                self.limits["cross_level"] = float(lim["cross_level_mm"])

    def calculate_exceedance_score(self, measured_mm: float, limit_mm: float) -> float:
        """
        Normalize physical metric into [0.0, 1.0] calibrated probability scale:
            Score = min(1.0, Measured / (2.0 * Limit))
        """
        if limit_mm <= 0.0:
            return 0.0
        return float(np.clip(abs(measured_mm) / (2.0 * limit_mm), 0.0, 1.0))

    def evaluate_features(self, geometry_features: Dict[str, Union[np.ndarray, float]]) -> List[CalibratedSignal]:
        """
        Evaluate a track segment's geometry feature arrays against RDSO/EN 13848 limits.
        Emits standard CalibratedSignal items for each fault detected.
        """
        signals: List[CalibratedSignal] = []

        # 1. Twist Exceedance (3m base)
        if "twist_3m_mm" in geometry_features:
            twist_arr = np.asarray(geometry_features["twist_3m_mm"])
            max_twist = float(np.max(np.abs(twist_arr))) if len(twist_arr) > 0 else 0.0
            limit = self.limits["twist_3m"]
            score = self.calculate_exceedance_score(max_twist, limit)
            fired = bool(score >= self.operating_threshold)
            
            if fired or score > 0.35:
                signals.append(
                    CalibratedSignal(
                        stream_name="geometry_physics",
                        raw_score=max_twist,
                        calibrated_prob=score,
                        predicted_class=DefectClass.TWIST_EXCEEDANCE,
                        is_anomaly=fired,
                        signal_type=SignalType.GEOMETRY_KNOWN,
                        threshold=self.operating_threshold,
                        explanation=f"RDSO 3m Twist: {max_twist:.2f}mm vs {limit:.1f}mm limit (Score: {score:.3f})",
                        metadata={
                            "feature": "twist_3m",
                            "limit_mm": limit,
                            "exceedance_mm": round(max_twist - limit, 3),
                            "severity": "critical" if max_twist >= limit else "high",
                        },
                    )
                )

        # 2. Gauge Deviation (Widening / Tightening)
        if "gauge_dev_mm" in geometry_features:
            gauge_arr = np.asarray(geometry_features["gauge_dev_mm"])
            max_gauge_dev = float(np.max(np.abs(gauge_arr))) if len(gauge_arr) > 0 else 0.0
            limit = self.limits["gauge_dev"]
            score = self.calculate_exceedance_score(max_gauge_dev, limit)
            fired = bool(score >= self.operating_threshold)

            if fired or score > 0.35:
                mean_dev = float(np.mean(gauge_arr)) if len(gauge_arr) > 0 else 0.0
                dev_type = "widening" if mean_dev >= 0.0 else "tightening"

                signals.append(
                    CalibratedSignal(
                        stream_name="geometry_physics",
                        raw_score=max_gauge_dev,
                        calibrated_prob=score,
                        predicted_class=DefectClass.GAUGE_WIDENING,
                        is_anomaly=fired,
                        signal_type=SignalType.GEOMETRY_KNOWN,
                        threshold=self.operating_threshold,
                        explanation=f"RDSO Gauge Deviation ({dev_type}): {max_gauge_dev:.2f}mm vs {limit:.1f}mm limit (Score: {score:.3f})",
                        metadata={
                            "feature": "gauge_deviation",
                            "deviation_type": dev_type,
                            "limit_mm": limit,
                            "exceedance_mm": round(max_gauge_dev - limit, 3),
                            "severity": "critical" if max_gauge_dev >= limit else "high",
                        },
                    )
                )

        # 3. Alignment Fault (Versine 10m)
        if "versine_10m_mm" in geometry_features:
            versine_arr = np.asarray(geometry_features["versine_10m_mm"])
            max_versine = float(np.max(np.abs(versine_arr))) if len(versine_arr) > 0 else 0.0
            limit = self.limits["versine_10m"]
            score = self.calculate_exceedance_score(max_versine, limit)
            fired = bool(score >= self.operating_threshold)

            if fired or score > 0.35:
                signals.append(
                    CalibratedSignal(
                        stream_name="geometry_physics",
                        raw_score=max_versine,
                        calibrated_prob=score,
                        predicted_class=DefectClass.ALIGNMENT_FAULT,
                        is_anomaly=fired,
                        signal_type=SignalType.GEOMETRY_KNOWN,
                        threshold=self.operating_threshold,
                        explanation=f"RDSO 10m Versine: {max_versine:.2f}mm vs {limit:.1f}mm limit (Score: {score:.3f})",
                        metadata={
                            "feature": "versine_10m",
                            "limit_mm": limit,
                            "exceedance_mm": round(max_versine - limit, 3),
                            "severity": "critical" if max_versine >= limit else "high",
                        },
                    )
                )

        # 4. Longitudinal Unevenness (10m chord)
        if "unevenness_10m_mm" in geometry_features:
            uneven_arr = np.asarray(geometry_features["unevenness_10m_mm"])
            max_uneven = float(np.max(np.abs(uneven_arr))) if len(uneven_arr) > 0 else 0.0
            limit = self.limits["unevenness_10m"]
            score = self.calculate_exceedance_score(max_uneven, limit)
            fired = bool(score >= self.operating_threshold)

            if fired or score > 0.35:
                signals.append(
                    CalibratedSignal(
                        stream_name="geometry_physics",
                        raw_score=max_uneven,
                        calibrated_prob=score,
                        predicted_class=DefectClass.ROUGH_TRACK,
                        is_anomaly=fired,
                        signal_type=SignalType.GEOMETRY_KNOWN,
                        threshold=self.operating_threshold,
                        explanation=f"RDSO 10m Longitudinal Unevenness: {max_uneven:.2f}mm vs {limit:.1f}mm limit (Score: {score:.3f})",
                        metadata={
                            "feature": "unevenness_10m",
                            "limit_mm": limit,
                            "exceedance_mm": round(max_uneven - limit, 3),
                            "severity": "critical" if max_uneven >= limit else "high",
                        },
                    )
                )

        return signals

    def evaluate_window(
        self,
        gauge_dev_mm: np.ndarray,
        twist_mm_per_m: np.ndarray,
        cant_mm: np.ndarray,
        versine_mm: Optional[np.ndarray] = None,
        unevenness_mm: Optional[np.ndarray] = None,
    ) -> List[CalibratedSignal]:
        """Convenience method for evaluating individual feature arrays directly."""
        features: Dict[str, Any] = {
            "gauge_dev_mm": gauge_dev_mm,
            "twist_3m_mm": twist_mm_per_m,
            "cant_mm": cant_mm,
        }
        if versine_mm is not None:
            features["versine_10m_mm"] = versine_mm
        if unevenness_mm is not None:
            features["unevenness_10m_mm"] = unevenness_mm
        return self.evaluate_features(features)

    def predict(self, telemetry_input: Union[pd.DataFrame, Dict[str, np.ndarray]]) -> List[CalibratedSignal]:
        """
        Process a raw telemetry DataFrame or dictionary through distance resampling,
        EN 13848 multi-chord physics calculations, and threshold evaluations.
        """
        if isinstance(telemetry_input, pd.DataFrame):
            df = telemetry_input
            ts = df["timestamp"].values if "timestamp" in df else np.arange(len(df)) * 0.01
            speed = df["speed_mps"].values if "speed_mps" in df else np.full(len(df), 20.0)
            sensor_streams = {
                col: df[col].values
                for col in df.columns
                if col not in ("timestamp", "speed_mps")
            }
        else:
            sensor_streams = telemetry_input
            ts = sensor_streams.get("timestamp", np.arange(len(next(iter(sensor_streams.values())))) * 0.01)
            speed = sensor_streams.get("speed_mps", np.full(len(ts), 20.0))

        # 1. Resample onto distance grid
        grid_chainage_m, resampled = self.resampler.resample_telemetry_batch(
            timestamps_s=ts,
            speeds_mps=speed,
            sensor_streams=sensor_streams,
        )

        n_samples = len(grid_chainage_m)
        roll_rad = resampled.get("roll_rad", np.zeros(n_samples))
        gauge_mm = resampled.get("gauge_mm", np.full(n_samples, self.nominal_gauge))
        lateral_mm = resampled.get("lat_accel_g", np.zeros(n_samples))
        vertical_mm = resampled.get("vert_accel_g", np.zeros(n_samples))

        step_m = float(np.mean(np.diff(grid_chainage_m))) if len(grid_chainage_m) > 1 else 0.25

        # 2. Compute features
        features = self.calculator.compute_all_features(
            roll_rad=roll_rad,
            lateral_pos_mm=lateral_mm,
            vertical_pos_mm=vertical_mm,
            gauge_mm=gauge_mm,
            step_m=step_m,
        )

        # 3. Evaluate thresholds
        return self.evaluate_features(features)
