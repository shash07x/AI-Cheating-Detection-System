import { BrowserRouter, Routes, Route } from "react-router-dom";
import CandidateApp from "./CandidateApp";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/join/:sessionId" element={<CandidateApp />} />
      </Routes>
    </BrowserRouter>
  );
}
