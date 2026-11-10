type Listener = () => void;

const listeners = new Set<Listener>();
let replayRequested = false;

export function requestIntroTourReplay() {
  replayRequested = true;
  for (const listener of listeners) listener();
}

export function consumeIntroTourReplay() {
  if (!replayRequested) {
    return false;
  }
  replayRequested = false;
  return true;
}

export function subscribeIntroTourReplay(listener: Listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
