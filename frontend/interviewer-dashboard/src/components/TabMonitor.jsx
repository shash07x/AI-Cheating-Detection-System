import { useEffect } from "react";
import socket from "../socket/socket";

export default function TabMonitor() {
  useEffect(() => {
    const handler = () => {
      if (document.hidden) {
        socket.emit("tab_violation", {
          reason: "Tab switched away"
        });
      }
    };

    document.addEventListener("visibilitychange", handler);
    return () =>
      document.removeEventListener("visibilitychange", handler);
  }, []);

  return null;
}
