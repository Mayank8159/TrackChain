# Sensor BOM and bring-up notes (camera, IMUs, GNSS, odometry).

# TrackChain Hardware & Sensor Bill of Materials (BOM)

| Subsystem | Component | Specifications | Interface |
|-----------|-----------|----------------|-----------|
| **Vision** | Basler ace 2 Pro Line Camera | Global shutter, 1920×1080 @ 60fps, IP67 enclosure | GigE Vision / PoE |
| **Optics** | Kowa 16mm Industrial Lens | Low distortion, vibration locked | C-Mount |
| **Inertial** | Lord MicroStrain 3DM-GX5-25 | 3-axis triaxial accelerometer (±50g) + Gyroscope | RS-422 / USB |
| **Positioning**| u-blox ZED-F9P RTK GNSS | Multi-band centimeter-level RTK positioning | UART / CAN |
| **Odometry** | Kübler Sendix Optical Wheel Encoder | 5000 pulses/rev for sub-millimeter chainage resolution | TTL / Quadrature |
| **Compute Edge**| NVIDIA Jetson AGX Orin | 275 TOPS AI performance, 64GB Unified Memory | PCIe / NVMe |
| **Laser Profiler**| Micro-Epsilon scanCONTROL 3000 | 2D/3D Laser profile measurement for track gauge | Gigabit Ethernet |
