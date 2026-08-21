// Zustand Store for 4-Step Edge Node Onboarding Wizard (tc.v1).

import { create } from "zustand";

export type HardwareType = "BOGIE_SCANNER" | "VISION_UNIT" | "GATEWAY" | "IMU_NODE";
export type ConnectionTestStatus = "IDLE" | "PENDING" | "SUCCESS" | "FAILED";

export interface NodeOnboardingState {
  isOpen: boolean;
  step: 1 | 2 | 3 | 4;
  nodeName: string;
  hardwareType: HardwareType;
  serialNumber: string;
  physicalLocation: string;
  apiKey: string | null;
  deviceId: string | null;
  connectionTestResult: ConnectionTestStatus;
  errorMessage: string | null;

  openWizard: () => void;
  closeWizard: () => void;
  setStep: (step: 1 | 2 | 3 | 4) => void;
  setNodeName: (name: string) => void;
  setHardwareType: (type: HardwareType) => void;
  setSerialNumber: (serial: string) => void;
  setPhysicalLocation: (loc: string) => void;
  setApiKey: (key: string | null) => void;
  setDeviceId: (id: string | null) => void;
  setConnectionTestResult: (result: ConnectionTestStatus) => void;
  setErrorMessage: (msg: string | null) => void;
  reset: () => void;
}

const initialState = {
  isOpen: false,
  step: 1 as const,
  nodeName: "",
  hardwareType: "BOGIE_SCANNER" as const,
  serialNumber: "",
  physicalLocation: "Northern Railway Carriage #482",
  apiKey: null,
  deviceId: null,
  connectionTestResult: "IDLE" as const,
  errorMessage: null,
};

export const useNodeOnboardingStore = create<NodeOnboardingState>((set) => ({
  ...initialState,

  openWizard: () =>
    set({
      ...initialState,
      isOpen: true,
      serialNumber: `SN-RPI5-${Math.floor(1000 + Math.random() * 9000)}`,
      nodeName: "Bogie Scanner Unit",
    }),

  closeWizard: () => set({ isOpen: false }),

  setStep: (step) => set({ step, errorMessage: null }),

  setNodeName: (nodeName) => set({ nodeName }),

  setHardwareType: (hardwareType) => set({ hardwareType }),

  setSerialNumber: (serialNumber) => set({ serialNumber }),

  setPhysicalLocation: (physicalLocation) => set({ physicalLocation }),

  setApiKey: (apiKey) => set({ apiKey }),

  setDeviceId: (deviceId) => set({ deviceId }),

  setConnectionTestResult: (connectionTestResult) => set({ connectionTestResult }),

  setErrorMessage: (errorMessage) => set({ errorMessage }),

  reset: () => set(initialState),
}));
