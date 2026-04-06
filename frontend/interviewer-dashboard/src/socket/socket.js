import { io } from "socket.io-client";

const socket = io("http://127.0.0.1:5000", {
  transports: ["websocket", "polling"],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 10,
  timeout: 30000,
  pingInterval: 10000,
  pingTimeout: 5000,
  autoConnect: true,
});

socket.on("connect", () => {
  console.log("✅ Interviewer connected:", socket.id);
  
  socket.emit("register_role", {
    session_id: "session_01",
    role: "interviewer"
  });
});

socket.on("disconnect", (reason) => {
  console.log("❌ Disconnected:", reason);
});

socket.on("connect_error", (error) => {
  console.error("❌ Connection error:", error);
});

// Keep-alive ping
setInterval(() => {
  if (socket.connected) {
    socket.emit("ping", { timestamp: Date.now() });
  }
}, 15000);

export default socket;