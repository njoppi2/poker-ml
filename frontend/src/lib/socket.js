const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "0.0.0.0"]);

export function resolveWebSocketUrl(
  currentLocation = typeof window !== "undefined" ? window.location : null,
  configuredUrl = import.meta.env.VITE_WS_URL,
) {
  const trimmedConfiguredUrl = configuredUrl?.trim();
  if (trimmedConfiguredUrl) {
    return trimmedConfiguredUrl;
  }

  if (!currentLocation || !LOCAL_HOSTNAMES.has(currentLocation.hostname)) {
    return null;
  }

  const websocketProtocol = currentLocation.protocol === "https:" ? "wss:" : "ws:";
  return `${websocketProtocol}//${currentLocation.hostname}:3002`;
}

export function buildStartGameMessage(gameType, chipMode) {
  return JSON.stringify({
    type: "start-game",
    gameType,
    chipMode,
  });
}
