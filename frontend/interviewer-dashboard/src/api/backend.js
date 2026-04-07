import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "https://shxsh07-ai-cheating-backend.hf.space";

const api = axios.create({
  baseURL: BACKEND_URL,
});

export default api;
