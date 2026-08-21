// Web Audio API sound synthesizer for real-time control room alarms (tc.v1).
// Zero external asset dependencies; purely synthesized low-latency audio.

class AudioManager {
  private ctx: AudioContext | null = null;
  private soundEnabled: boolean = false;

  public isEnabled(): boolean {
    return this.soundEnabled;
  }

  public setEnabled(enabled: boolean): void {
    this.soundEnabled = enabled;
    if (enabled && !this.ctx) {
      this.initContext();
    }
  }

  private initContext(): void {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    } catch {
      // Audio context blocked or unsupported
    }
  }

  private ensureContext(): AudioContext | null {
    if (!this.ctx) {
      this.initContext();
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  /**
   * Dual-tone alarm siren for CRITICAL Immediate Action Limits (IAL)
   */
  public playCriticalAlarm(): void {
    if (!this.soundEnabled) return;
    const ctx = this.ensureContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sawtooth";
      // Dual tone modulation: 880Hz (A5) -> 587Hz (D5) -> 880Hz
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.linearRampToValueAtTime(587, now + 0.15);
      osc.frequency.linearRampToValueAtTime(880, now + 0.3);
      osc.frequency.linearRampToValueAtTime(587, now + 0.45);
      osc.frequency.linearRampToValueAtTime(880, now + 0.6);

      gain.gain.setValueAtTime(0.18, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.7);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.7);
    } catch {
      // Ignore audio synthesis errors
    }
  }

  /**
   * Sharp double digital beep for HIGH severity alerts
   */
  public playHighWarning(): void {
    if (!this.soundEnabled) return;
    const ctx = this.ensureContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;

      // Beep 1
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = "square";
      osc1.frequency.setValueAtTime(1174.66, now); // D6
      gain1.gain.setValueAtTime(0.12, now);
      gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(now);
      osc1.stop(now + 0.1);

      // Beep 2
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = "square";
      osc2.frequency.setValueAtTime(1479.98, now + 0.14); // F#6
      gain2.gain.setValueAtTime(0.12, now + 0.14);
      gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.26);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(now + 0.14);
      osc2.stop(now + 0.26);
    } catch {
      // Ignore audio synthesis errors
    }
  }

  /**
   * Soft pleasant confirmation chime for Operator Acknowledgment
   */
  public playAckChime(): void {
    if (!this.soundEnabled) return;
    const ctx = this.ensureContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(659.25, now); // E5
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15); // A5

      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.3);
    } catch {
      // Ignore audio synthesis errors
    }
  }
}

export const audioManager = new AudioManager();
