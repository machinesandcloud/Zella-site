export type WSMessage = {
  channel: string;
  timestamp: string;
};

export const connectWebSocket = (path: string, onMessage: (msg: WSMessage) => void) => {
  const base = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
  const ws = new WebSocket(`${base}${path}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data as WSMessage);
    } catch {
      // ignore parse errors
    }
  };

  ws.onerror = (error) => {
    console.warn("WebSocket error:", error);
  };

  ws.onclose = () => {
    console.log("WebSocket closed");
  };

  return ws;
};
