import { describe, expect, it } from "vitest";

import { buildStartGameMessage, resolveWebSocketUrl } from "./socket";

describe("resolveWebSocketUrl", () => {
  it("prefers an explicit configured websocket url", () => {
    const resolvedUrl = resolveWebSocketUrl(
      { hostname: "example.com", protocol: "https:" },
      "wss://api.example.com/ws",
    );

    expect(resolvedUrl).toBe("wss://api.example.com/ws");
  });

  it("uses the local backend default for localhost", () => {
    const resolvedUrl = resolveWebSocketUrl({
      hostname: "localhost",
      protocol: "http:",
    });

    expect(resolvedUrl).toBe("ws://localhost:3002");
  });

  it("returns null for non-localhost usage without configuration", () => {
    const resolvedUrl = resolveWebSocketUrl(
      { hostname: "njoppi2.github.io", protocol: "https:" },
      "",
    );

    expect(resolvedUrl).toBeNull();
  });
});

describe("buildStartGameMessage", () => {
  it("builds the start-game envelope expected by the backend", () => {
    expect(JSON.parse(buildStartGameMessage("Leduc", "reset_each_round"))).toEqual({
        chipMode: "reset_each_round",
        gameType: "Leduc",
        type: "start-game",
      });
  });
});
