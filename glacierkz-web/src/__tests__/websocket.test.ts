import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WebSocketClient } from "@/lib/websocket";

let lastSocket: {
  readyState: number;
  send: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
  onmessage: ((ev: MessageEvent) => void) | null;
};

describe("WebSocketClient", () => {
  let client: WebSocketClient;

  beforeEach(() => {
    class MockWebSocket {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;

      readyState = MockWebSocket.CONNECTING;
      send = vi.fn();
      close = vi.fn();
      onopen: ((ev: Event) => void) | null = null;
      onclose: ((ev: CloseEvent) => void) | null = null;
      onerror: ((ev: Event) => void) | null = null;
      onmessage: ((ev: MessageEvent) => void) | null = null;

      constructor(public url: string) {
        lastSocket = this;
      }
    }

    vi.stubGlobal("WebSocket", MockWebSocket);
    client = new WebSocketClient({ url: "ws://localhost:8000/ws", reconnect: false });
  });

  afterEach(() => {
    client.disconnect();
    vi.unstubAllGlobals();
  });

  it("initializes with disconnected status", () => {
    expect(client.status).toBe("disconnected");
  });

  it("creates connection on connect", () => {
    client.connect();
    expect(lastSocket.url).toBe("ws://localhost:8000/ws");
  });

  it("sends messages", () => {
    client.connect();
    lastSocket.readyState = 1;
    client.send({ type: "test", data: "hello" });
    expect(lastSocket.send).toHaveBeenCalledWith(JSON.stringify({ type: "test", data: "hello" }));
  });

  it("does not send when not connected", () => {
    expect(() => client.send({ type: "test" })).toThrow("WebSocket is not connected");
  });

  it("closes connection on disconnect", () => {
    client.connect();
    client.disconnect();
    expect(lastSocket.close).toHaveBeenCalledWith(1000, "Client disconnect");
  });

  it("handles message events", () => {
    const handler = vi.fn();
    client.on("message", handler);
    client.connect();
    lastSocket.onmessage!({
      data: JSON.stringify({ type: "message", data: "hello", timestamp: "2020-01-01" }),
    } as MessageEvent);
    expect(handler).toHaveBeenCalledWith(expect.objectContaining({ type: "message", data: "hello" }));
  });
});
