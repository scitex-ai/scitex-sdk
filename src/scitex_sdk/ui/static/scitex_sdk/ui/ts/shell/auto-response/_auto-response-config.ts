/**
 * Auto-Response Configuration & Types.
 *
 * Ported from scitex-cloud's auto-response-config.ts.
 */

import type { ClaudeState } from "./_claude-state-detector";

export function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  return hash;
}

export interface SentPosition {
  bufferLength: number;
  time: number;
}

export type SendFn = (text: string) => void;
export type GetTermFn = () => any | null;

export interface AutoResponseConfig {
  interval: number;
  responses: Record<string, string | null>;
  sameStateDelay: number;
  burstLimit: number;
  burstWindow: number;
  safeDelay: number;
  ynRecheckDelay: number;
  stuckStateThreshold: number;
  sendingTimeout: number;
  nilStateRetryInterval: number;
  nilStateWideMultiplier: number;
  periodicInterval: number;
  verifyDelay: number;
  permissionRetryMax: number;
  idleLoopMax: number;
  minWorkDuration: number;
}

export const DEFAULT_CONFIG: AutoResponseConfig = {
  interval: 1500,
  responses: {
    y_n: "1",
    y_y_n: "2",
    waiting: "/speak-signature",
    suggestion: "",
  },
  sameStateDelay: 1500,
  burstLimit: 10,
  burstWindow: 3000,
  safeDelay: 500,
  ynRecheckDelay: 1000,
  stuckStateThreshold: 15000,
  sendingTimeout: 30000,
  nilStateRetryInterval: 5000,
  nilStateWideMultiplier: 4,
  periodicInterval: 300000,
  verifyDelay: 2000,
  permissionRetryMax: 1,
  idleLoopMax: 3,
  minWorkDuration: 30000,
};

export type { ClaudeState };
