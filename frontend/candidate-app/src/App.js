import { useState } from "react";
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

  if (!admitted) {
    return <LoginPage onAdmitted={handleAdmitted} />;
  }

  return <CandidateApp candidateId={candidateId} sessionId={sessionId} />;
}
