# Unit tests for physics feature math.

import numpy as np
from ml.features.en13848 import EN13848PhysicsCalculator


def test_gauge_deviation():
    calc = EN13848PhysicsCalculator(nominal_gauge_mm=1435.0)
    measured = np.array([1435.0, 1438.0, 1445.0])
    dev = calc.compute_gauge_deviation(measured)
    assert np.allclose(dev, np.array([0.0, 3.0, 10.0]))


def test_twist_calculation():
    calc = EN13848PhysicsCalculator(twist_base_length_m=3.0)
    # cant changing 6mm over 3m (12 steps of 0.25m)
    cant = np.zeros(20)
    cant[12:] = 6.0
    twist = calc.compute_twist(cant, step_m=0.25)
    assert twist[12] == 2.0  # 6mm / 3m = 2 mm/m
