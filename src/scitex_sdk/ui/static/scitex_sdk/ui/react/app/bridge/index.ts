/** App bridge runtime — generic utilities for docking apps into scitex-cloud. */

export type {
  BridgeConfig,
  BridgeMountOptions,
  AppMounter,
  AppUnmounter,
} from "./BridgeContract";

export {
  installFetchOverride,
  mountReactApp,
  unmountReactApp,
} from "./GenericMountPoint";

export { emitBridgeEvent, onBridgeEvent } from "./GenericEventBus";
