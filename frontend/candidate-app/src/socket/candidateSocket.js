import { io } from "socket.io-client";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";

const socket = io(BACKEND_URL, {
  transports: ["websocket", "polling"],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 10,
  timeout: 20000,
  autoConnect: true,
});

socket.on("connect", () => {
  console.log("✅ Candidate connected:", socket.id);
});

socket.on("disconnect", (reason) => {
  console.log("❌ Disconnected:", reason);
});

socket.on("connect_error", (error) => {
  console.error("❌ Connection error:", error.message);
});

export default socket;