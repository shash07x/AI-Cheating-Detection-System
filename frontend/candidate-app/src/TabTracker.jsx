import { useEffect } from "react";
import socket from "./socket/candidateSocket";

export default function TabTracker({ sessionId }) {
  useEffect(() => {
    const onBlur = () => {
      socket.emit("tab_switch", { session_id: sessionId });
    };

    window.addEventListener("blur", onBlur);
    return () => window.removeEventListener("blur", onBlur);
  }, [sessionId]);

  return null;
}
