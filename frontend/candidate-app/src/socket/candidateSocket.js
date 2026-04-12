import { io } from "socket.io-client";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "https://shxsh07-ai-cheating-backend.hf.space";

console.log("🔌 Candidate socket connecting to:", BACKEND_URL);

const socket = io(BACKEND_URL, {
  // Use polling only — HF Spaces reverse proxy can drop WebSocket upgrades
  transports: ["polling"],
  reconnection: true,
  reconnectionDelay: 2000,
  reconnectionDelayMax: 10000,
  reconnectionAttempts: 30,
  // HF free tier Spaces sleep after inactivity and take 30-60s to wake up
  timeout: 120000,
  autoConnect: true,
  upgrade: false,
});

socket.on("connect", () => {
  console.log("✅ Candidate connected:", socket.id);
});

socket.on("disconnect", (reason) => {
  console.log("❌ Disconnected:", reason);
});

socket.on("connect_error", (error) => {
  console.warn("⚠️ Connection error (retrying...):", error.message);
});

export default socket;