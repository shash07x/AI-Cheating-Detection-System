import axios from "axios";

const API = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000",
  timeout: 15000,
});

// ---- VIDEO ----
export const analyzeVideo = () => API.get("/video/analyze");

// ---- AUDIO ----
export const analyzeAudio = (audioFile) => {
  const formData = new FormData();
  formData.append("audio", audioFile);

  return API.post("/audio/analyze", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

// ---- FINAL SCORE ----
export const finalizeSession = (payload) =>
  API.post("/ai/finalize", payload);

// ---- DASHBOARD ----
export const fetchSessions = () => API.get("/dashboard/sessions");

export default API;
