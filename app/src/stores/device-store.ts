// Zustand store for Zero-Touch Edge Node Auto-Discovery & Live Fleet State (tc.v1).

import { create } from "zustand";
import type { Device } from "@/lib/types";
import { sseClient } from "@/lib/sse";

interface DeviceStoreState {
  discoveredDevices: Device[];
  newlyDiscoveredIds: string[];
  latestDiscoveredNode: Device | null;
  addDiscoveredNode: (raw: any) => Device;
  clearNewBadge: (deviceId: string) => void;
  getAllDevicesWithCoords: () => Device[];
}

export const useDeviceStore = create<DeviceStoreState>((set, get) => ({
  discoveredDevices: [],
  newlyDiscoveredIds: [],
  latestDiscoveredNode: null,

  addDiscoveredNode: (raw: any) => {
    const deviceId = raw.deviceId || raw.device_id || `CAM-${Date.now().toString().slice(-4)}`;
    const deviceName = raw.deviceName || raw.device_name || `Edge Node ${deviceId}`;
    const hardwareVersion = raw.hardwareVersion || raw.hardware_version || "Raspberry Pi 5";
    const firmwareVersion = raw.firmwareVersion || raw.firmware_version || "v1.0.0";
    const cameraModel = raw.cameraModel || raw.camera_model || "Sony IMX477";
    const status = raw.status || "pending_approval";
    const latitude = typeof raw.latitude === "number" ? raw.latitude : (typeof raw.lat === "number" ? raw.lat : 28.535);
    const longitude = typeof raw.longitude === "number" ? raw.longitude : (typeof raw.lon === "number" ? raw.lon : 77.284);

    const newDevice: Device = {
      deviceId,
      deviceName,
      hardwareVersion,
      firmwareVersion,
      cameraModel,
      status: status as any,
      latitude,
      longitude,
      isDiscovered: true,
      discoveredAt: new Date().toISOString(),
      lastSeenAt: new Date().toISOString(),
    };

    set((state) => {
      // Deduplicate by deviceId
      const filtered = state.discoveredDevices.filter((d) => d.deviceId !== deviceId);
      const newIds = Array.from(new Set([deviceId, ...state.newlyDiscoveredIds]));

      return {
        discoveredDevices: [newDevice, ...filtered],
        newlyDiscoveredIds: newIds,
        latestDiscoveredNode: newDevice,
      };
    });

    return newDevice;
  },

  clearNewBadge: (deviceId: string) => {
    set((state) => ({
      newlyDiscoveredIds: state.newlyDiscoveredIds.filter((id) => id !== deviceId),
    }));
  },

  getAllDevicesWithCoords: () => {
    return get().discoveredDevices.filter((d) => typeof d.latitude === "number" && typeof d.longitude === "number");
  },
}));

// Auto-wire SSE subscription in browser context
if (typeof window !== "undefined") {
  sseClient.subscribeDeviceDiscovered((payload) => {
    if (payload) {
      useDeviceStore.getState().addDiscoveredNode(payload);
    }
  });
}
