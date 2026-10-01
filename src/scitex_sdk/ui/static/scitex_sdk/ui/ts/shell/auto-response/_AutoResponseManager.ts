/**
 * Auto-Response Manager for Claude Code CLI.
 *
 * Polls xterm.js terminal buffer, detects Claude Code CLI prompt states,
 * and automatically sends appropriate responses.
 *
 * Ported from emacs-claude-code via scitex-cloud.
 * Pure frontend — no backend dependency.
 */

import {
  detectState,
  readTerminalBuffer,
  DETECTION_BUFFER_SIZE,
} from "./_claude-state-detector";
import {
  type AutoResponseConfig,
  type ClaudeState,
  type SendFn,
  type GetTermFn,
  type SentPosition,
  DEFAULT_CONFIG,
  simpleHash,
} from "./_auto-response-config";

export type { AutoResponseConfig } from "./_auto-response-config";

export class AutoResponseManager {
  private config: AutoResponseConfig;
  private enabled = false;
  private timerId: ReturnType<typeof setInterval> | null = null;
  private sendFn: SendFn;
  private getTermFn: GetTermFn;
  private lastState: ClaudeState = null;
  private lastResponseTime = 0;
  private responseTimestamps: number[] = [];
  private sentPositions: SentPosition[] = [];
  private sending = false;
  private sendingTimestamp = 0;
  private stateFirstSeenTime = 0;
  private stateFirstSeenState: ClaudeState = null;
  private nilStateStart = 0;
  private lastContentHash = 0;
  private periodicTimerId: ReturnType<typeof setInterval> | null = null;
  private idleLoopCount = 0;
  private lastWaitingResponseTime = 0;
  private onStateChangeCallbacks: Array<
    (state: ClaudeState, enabled: boolean) => void
  > = [];
  private onResponseSentCallbacks: Array<
    (state: ClaudeState, response: string) => void
  > = [];

  constructor(
    sendFn: SendFn,
    getTermFn: GetTermFn,
    config?: Partial<AutoResponseConfig>,
  ) {
    this.sendFn = sendFn;
    this.getTermFn = getTermFn;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  isEnabled(): boolean {
    return this.enabled;
  }

  enable(): void {
    if (this.enabled) return;
    this.enabled = true;
    this.resetTracking();
    this.startTimer();
    this.startPeriodicTimer();
    this.notifyStateChange(null);
    console.log("[AutoResponse] Enabled");
  }

  disable(): void {
    if (!this.enabled) return;
    this.enabled = false;
    this.stopTimer();
    this.stopPeriodicTimer();
    this.notifyStateChange(null);
    console.log("[AutoResponse] Disabled");
  }

  toggle(): boolean {
    if (this.enabled) this.disable();
    else this.enable();
    return this.enabled;
  }

  onStateChange(cb: (state: ClaudeState, enabled: boolean) => void): void {
    this.onStateChangeCallbacks.push(cb);
  }

  onResponseSent(cb: (state: ClaudeState, response: string) => void): void {
    this.onResponseSentCallbacks.push(cb);
  }

  updateConfig(partial: Partial<AutoResponseConfig>): void {
    this.config = { ...this.config, ...partial };
    if (this.enabled) {
      this.stopTimer();
      this.stopPeriodicTimer();
      this.startTimer();
      this.startPeriodicTimer();
    }
  }

  private startTimer(): void {
    this.stopTimer();
    this.timerId = setInterval(() => this.tick(), this.config.interval);
    setTimeout(() => this.tick(), 100);
  }

  private stopTimer(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  private startPeriodicTimer(): void {
    this.stopPeriodicTimer();
    if (this.config.periodicInterval <= 0) return;
    this.periodicTimerId = setInterval(() => {
      if (!this.enabled || this.sending) return;
      const term = this.getTermFn();
      if (!term) return;
      const state = detectState(
        readTerminalBuffer(term, DETECTION_BUFFER_SIZE),
      );
      if (state === "running") return;
      this.sendFn("\r");
    }, this.config.periodicInterval);
  }

  private stopPeriodicTimer(): void {
    if (this.periodicTimerId !== null) {
      clearInterval(this.periodicTimerId);
      this.periodicTimerId = null;
    }
  }

  private tick(): void {
    if (!this.enabled) return;
    if (
      this.sending &&
      this.sendingTimestamp > 0 &&
      Date.now() - this.sendingTimestamp > this.config.sendingTimeout
    ) {
      this.sending = false;
    }
    if (this.sending) return;

    const term = this.getTermFn();
    if (!term) return;

    const bufferText = readTerminalBuffer(term, DETECTION_BUFFER_SIZE);
    if (!bufferText) return;

    const hash = simpleHash(bufferText);
    const contentChanged = hash !== this.lastContentHash;
    this.lastContentHash = hash;

    let state = detectState(bufferText);

    if (!state) {
      if (this.nilStateStart === 0) {
        this.nilStateStart = Date.now();
      } else if (
        Date.now() - this.nilStateStart >
        this.config.nilStateRetryInterval
      ) {
        const wideText = readTerminalBuffer(
          term,
          DETECTION_BUFFER_SIZE * this.config.nilStateWideMultiplier,
        );
        state = detectState(wideText);
      }
    } else {
      this.nilStateStart = 0;
    }

    this.notifyStateChange(state);
    this.trackStateDuration(state);

    if (!state || state === "running" || state === "user_typing") return;
    if (
      !contentChanged &&
      state !== "y_n" &&
      state !== "y_y_n" &&
      state !== "suggestion"
    )
      return;
    if (this.alreadySentAtPosition(term)) return;
    if (this.shouldThrottle(state)) return;

    this.sendResponse(state, term);
  }

  private async sendResponse(state: ClaudeState, term: any): Promise<void> {
    if (!state) return;

    let effectiveState = state;
    if (state === "y_n") {
      this.sending = true;
      this.sendingTimestamp = Date.now();
      await this.sleep(this.config.ynRecheckDelay);
      const recheck = detectState(
        readTerminalBuffer(term, DETECTION_BUFFER_SIZE),
      );
      if (recheck === "y_y_n") effectiveState = "y_y_n";
      this.sending = false;
    }

    if (effectiveState === "waiting") {
      const now = Date.now();
      if (now - this.lastWaitingResponseTime > this.config.minWorkDuration)
        this.idleLoopCount = 0;
      if (this.idleLoopCount >= this.config.idleLoopMax) return;
      this.idleLoopCount++;
      this.lastWaitingResponseTime = now;
    }

    const response = this.config.responses[effectiveState];
    if (response === undefined || response === null) return;

    this.sending = true;
    this.sendingTimestamp = Date.now();

    try {
      await this.sleep(this.config.safeDelay);
      if (response.length > 0) this.sendFn(response);
      await this.sleep(200);
      this.sendFn("\r");
      await this.sleep(this.config.safeDelay);
      this.updateTracking(effectiveState, term);
      this.notifyResponseSent(effectiveState, response);
      console.log(
        `[AutoResponse] Sent "${response || "↵"}" for state: ${effectiveState}`,
      );
      await this.verifySend(effectiveState, term);
    } finally {
      this.sending = false;
    }
  }

  private async verifySend(state: ClaudeState, term: any): Promise<void> {
    const isPermission = state === "y_n" || state === "y_y_n";
    if (!isPermission) return;
    for (let i = 0; i < this.config.permissionRetryMax; i++) {
      await this.sleep(this.config.verifyDelay);
      const newState = detectState(
        readTerminalBuffer(term, DETECTION_BUFFER_SIZE),
      );
      if (newState !== state) return;
      const response = this.config.responses[state];
      if (response !== undefined && response !== null) {
        if (response.length > 0) this.sendFn(response);
        await this.sleep(200);
        this.sendFn("\r");
      }
    }
  }

  private shouldThrottle(state: ClaudeState): boolean {
    const now = Date.now();
    if (
      state === this.lastState &&
      now - this.lastResponseTime < this.config.sameStateDelay
    )
      return true;
    const windowStart = now - this.config.burstWindow;
    return (
      this.responseTimestamps.filter((t) => t >= windowStart).length >=
      this.config.burstLimit
    );
  }

  private alreadySentAtPosition(term: any): boolean {
    const bufLen = term.buffer?.active?.length ?? 0;
    const currentState = detectState(
      readTerminalBuffer(term, DETECTION_BUFFER_SIZE),
    );
    if (currentState !== this.lastState) return false;
    return this.sentPositions.some(
      (sp) => Math.abs(bufLen - sp.bufferLength) < 100,
    );
  }

  private trackStateDuration(state: ClaudeState): void {
    if (state && state === this.stateFirstSeenState) {
      if (
        (state === "y_n" || state === "y_y_n" || state === "waiting") &&
        this.stateFirstSeenTime > 0 &&
        Date.now() - this.stateFirstSeenTime > this.config.stuckStateThreshold
      ) {
        this.stateFirstSeenTime = Date.now();
        this.sentPositions = [];
        const term = this.getTermFn();
        if (term) this.sendResponse(state, term);
      }
    } else {
      this.stateFirstSeenState = state;
      this.stateFirstSeenTime = state ? Date.now() : 0;
    }
  }

  private updateTracking(state: ClaudeState, term: any): void {
    const now = Date.now();
    this.lastState = state;
    this.lastResponseTime = now;
    this.responseTimestamps.push(now);
    const bufLen = term.buffer?.active?.length ?? 0;
    this.sentPositions.push({ bufferLength: bufLen, time: now });
    const cutoff = now - 60000;
    this.responseTimestamps = this.responseTimestamps.filter(
      (t) => t >= cutoff,
    );
    this.sentPositions = this.sentPositions.filter((sp) => sp.time >= cutoff);
  }

  private resetTracking(): void {
    this.lastState = null;
    this.lastResponseTime = 0;
    this.responseTimestamps = [];
    this.sentPositions = [];
    this.sending = false;
    this.sendingTimestamp = 0;
    this.stateFirstSeenTime = 0;
    this.stateFirstSeenState = null;
    this.nilStateStart = 0;
    this.lastContentHash = 0;
    this.idleLoopCount = 0;
    this.lastWaitingResponseTime = 0;
  }

  private notifyStateChange(state: ClaudeState): void {
    for (const cb of this.onStateChangeCallbacks) {
      try {
        cb(state, this.enabled);
      } catch {}
    }
  }

  private notifyResponseSent(state: ClaudeState, response: string): void {
    for (const cb of this.onResponseSentCallbacks) {
      try {
        cb(state, response);
      } catch {}
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
