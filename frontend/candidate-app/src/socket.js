import { io } from "socket.io-client";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";

const socket = io(BACKEND_URL, {
  transports: ["websocket"],
});

export default socket;
