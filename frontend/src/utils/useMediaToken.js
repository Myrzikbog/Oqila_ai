import { useSyncExternalStore } from 'react';
import { getMediaToken, subscribeMediaToken } from './session';

/** Re-renders the component when the media token arrives or is renewed, so withToken() URLs stay valid. */
export function useMediaToken() {
  return useSyncExternalStore(subscribeMediaToken, getMediaToken, () => null);
}
