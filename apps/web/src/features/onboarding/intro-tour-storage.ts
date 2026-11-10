const PREFIX = "koicloud:intro-tour-v1:";

export function introTourStorageKey(userId: string) {
  return `${PREFIX}${userId}`;
}

export function isIntroTourDone(userId: string) {
  return window.localStorage.getItem(introTourStorageKey(userId)) === "done";
}

export function markIntroTourDone(userId: string) {
  window.localStorage.setItem(introTourStorageKey(userId), "done");
}

export function clearIntroTourDone(userId: string) {
  window.localStorage.removeItem(introTourStorageKey(userId));
}
