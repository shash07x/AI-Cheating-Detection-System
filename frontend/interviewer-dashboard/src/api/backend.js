import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";

const api = axios.create({
  baseURL: BACKEND_URL,
});

export default api;
