import { io } from "socket.io-client";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "https://shxsh07-ai-cheating-backend.hf.space";

const socket = io(BACKEND_URL, {
  transports: ["websocket"],
});

export default socket;
