import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import CandidateApp from './CandidateApp';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <CandidateApp />
  </React.StrictMode>
);

reportWebVitals();
