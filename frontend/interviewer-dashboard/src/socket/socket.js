import { io } from "socket.io-client";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "https://shxsh07-ai-cheating-backend.hf.space";

console.log("🔌 Socket connecting to:", BACKEND_URL);

const socket = io(BACKEND_URL, {
  // Use polling only — HF Spaces reverse proxy can drop WebSocket upgrades
  transports: ["polling"],
  reconnection: true,
  reconnectionDelay: 2000,
  reconnectionDelayMax: 10000,
  reconnectionAttempts: 30,
  // HF free tier Spaces sleep after inactivity and take 30-60s to wake up
  // Set timeout high enough to handle cold starts
  timeout: 120000,
  autoConnect: true,
  // Disable WebSocket upgrade — HF Spaces polling is more reliable
  upgrade: false,
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
  console.warn("⚠️ Connection error (retrying...):", error.message);
});

// Keep-alive ping to prevent HF Space from sleeping
setInterval(() => {
  if (socket.connected) {
    socket.emit("ping", { timestamp: Date.now() });
  }
}, 15000);

export default socket;