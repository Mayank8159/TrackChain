import numpy as np
from ml.features.en13848 import EN13848PhysicsCalculator

calc = EN13848PhysicsCalculator()
# create dummy cant
cant = np.array([10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 15.0]) # 13 elements, index 12 is 15.0
# step = 0.25, base = 3.0 => base_samples = 12
# twist at index 12 should be cant[12] - cant[0] = 15.0 - 10.0 = 5.0
twist = calc.compute_twist(cant, base_length_m=3.0, step_m=0.25)
print("Twist at index 12:", twist[12])

# Versine
y = np.array([0.0] * 40 + [10.0] + [0.0] * 40) # anomaly at index 40
# chord = 10.0 => half_chord = 5.0 => half_chord_samples = 20
# versine at index 40 = y[40] - (y[20] + y[60])/2 = 10 - 0 = 10
# Wait, compute_chord_versine applies highpass filter by default. Disable it for pure math check.
versine = calc.compute_chord_versine(y, chord_length_m=10.0, step_m=0.25, filter_curvature=False)
print("Versine at index 40:", versine[40])
