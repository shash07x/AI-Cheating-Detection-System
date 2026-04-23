import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import LoginPage from "./LoginPage";
import CandidateApp from "./CandidateApp";

export default function App() {
  const [admitted, setAdmitted] = useState(false);
  const [candidateId, setCandidateId] = useState("");
  const [sessionId, setSessionId] = useState("session_01");

  const handleAdmitted = (cId, sId) => {
    setCandidateId(cId);
    setSessionId(sId);
    setAdmitted(true);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="*"
          element={
            admitted ? (
              <CandidateApp candidateId={candidateId} sessionId={sessionId} />
            ) : (
              <LoginPage onAdmitted={handleAdmitted} />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
