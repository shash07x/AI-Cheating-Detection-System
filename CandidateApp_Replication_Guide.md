# Candidate App Replication Guide

## Purpose

This document explains exactly how the active Three.js-based `candidate-app` is built in this repository, which files are linked together, which backend endpoints it depends on, and what must be reproduced in a clone to get the same candidate-side behavior and UI.

The active Three.js implementation is in:

`frontend/candidate-app`

There is also a separate app at `frontend_v2/candidate-app`, but that one does not currently contain the Three.js scene used by the active candidate experience.

## High-Level Summary

The candidate app is a Create React App project that renders a single-page proctoring interface.

It combines:

- a voice-reactive Three.js background scene
- microphone capture and audio-level analysis
- webcam capture and frame upload
- tab-switch tracking
- socket communication to the backend
- an overlay UI showing microphone, camera, and speaking activity

The exact active render path is:

`public/index.html` -> `src/index.js` -> `src/CandidateApp.jsx`

The Three.js scene is rendered by:

`src/SpeakingScene.jsx`

The scene is driven by live microphone energy generated in:

`src/MicrophoneSender.jsx`

## Project Type and Build System

The project uses Create React App.

### Package File

`frontend/candidate-app/package.json`

### Build Scripts

```json
"scripts": {
  "start": "react-scripts start",
  "build": "react-scripts build",
  "test": "react-scripts test",
  "eject": "react-scripts eject"
}
```

### Required Dependencies

These are the important dependencies used by the current implementation:

```json
"react": "^19.2.4",
"react-dom": "^19.2.4",
"react-scripts": "5.0.1",
"three": "^0.183.2",
"socket.io": "^4.8.3",
"socket.io-client": "^4.8.3"
```

### Commands

From `frontend/candidate-app`:

```bash
npm install
npm start
```

Production build:

```bash
npm run build
```

## Active Startup Flow

The candidate app currently does not start from `App.jsx`.

The real startup chain is:

1. `public/index.html` provides the root DOM node.
2. `src/index.js` mounts React into that root.
3. `src/index.js` renders `CandidateApp` directly.
4. `CandidateApp.jsx` mounts the Three.js scene and all proctoring helpers.

### `public/index.html`

Key mount point:

```html
<div id="root"></div>
```

This file also sets metadata such as:

- page title: `Candidate Interview`
- description mentioning the voice-reactive Three.js environment

### `src/index.js`

This is the actual app entrypoint:

```js
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import CandidateApp from "./CandidateApp";
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <CandidateApp />
  </React.StrictMode>
);

reportWebVitals();
```

This means the clone must also render `CandidateApp` directly from `index.js` if you want the same current behavior.

## Main Component Graph

The active file graph is:

```text
public/index.html
  -> src/index.js
    -> src/index.css
    -> src/CandidateApp.jsx
      -> src/App.css
      -> src/SpeakingScene.jsx
        -> three
      -> src/MicrophoneSender.jsx
        -> src/socket/candidateSocket.js
      -> src/WebcamSender.jsx
      -> src/TabTracker.jsx
        -> src/socket/candidateSocket.js
```

## File-by-File Breakdown

## 1. `src/CandidateApp.jsx`

### Role

This is the root candidate screen component.

### Imports

```js
import { useState } from "react";
import WebcamSender from "./WebcamSender";
import MicrophoneSender from "./MicrophoneSender";
import TabTracker from "./TabTracker";
import SpeakingScene from "./SpeakingScene";
import "./App.css";
```

### Main Responsibilities

- stores `audioLevel`
- stores microphone status
- stores camera status
- renders the Three.js canvas background
- renders the content overlay and status cards
- mounts the webcam sender
- mounts the microphone sender
- mounts the tab tracker

### Key State

```js
const [audioLevel, setAudioLevel] = useState(0);
const [micStatus, setMicStatus] = useState({ state: "requesting" });
const [cameraStatus, setCameraStatus] = useState({ state: "requesting" });
const sessionId = "session_01";
```

### Key Wiring

The Three.js scene receives the current mic level:

```jsx
<SpeakingScene audioLevel={audioLevel} />
```

The microphone component sends updates into `setAudioLevel`:

```jsx
<MicrophoneSender
  sessionId={sessionId}
  onAudioLevel={setAudioLevel}
  onStatusChange={setMicStatus}
/>
```

The camera component reports camera status:

```jsx
<WebcamSender sessionId={sessionId} onStatusChange={setCameraStatus} />
```

The tab-tracking component reports tab changes:

```jsx
<TabTracker sessionId={sessionId} />
```

### Why This File Matters

If this file is not rebuilt with the same imports and prop links, the clone will not reproduce the same behavior because this is where the scene, mic, camera, and tab logic are connected together.

## 2. `src/SpeakingScene.jsx`

### Role

This file contains the actual Three.js-based animated candidate scene.

### Import

```js
import * as THREE from "three";
```

### Component Contract

It accepts:

```js
audioLevel
```

### Main Three.js Objects Created

- `THREE.Scene`
- `THREE.FogExp2`
- `THREE.PerspectiveCamera`
- `THREE.WebGLRenderer`
- `THREE.AmbientLight`
- `THREE.PointLight`
- `THREE.Group`
- `THREE.IcosahedronGeometry`
- `THREE.MeshPhongMaterial`
- `THREE.SphereGeometry`
- `THREE.MeshBasicMaterial`
- `THREE.PlaneGeometry`
- `THREE.BufferGeometry`
- `THREE.BufferAttribute`
- `THREE.Points`
- `THREE.PointsMaterial`
- `THREE.Clock`

### Visual Elements Built

The scene constructs:

- a wireframe glowing globe
- an outer glowing shell
- multiple colored nebula planes
- a large star field
- ambient, key, and rim lights
- fog for depth

### Audio-Reactive Behavior

The `audioLevel` value directly influences:

- globe rotation speed
- globe scaling
- shell scaling
- shell opacity
- globe material opacity
- globe emissive intensity
- nebula position and opacity
- nebula scale
- star size
- camera `z` position

This is what makes the background feel voice-reactive.

### Mounting Logic

The component returns:

```jsx
<div className="scene-canvas" ref={mountRef} aria-hidden="true" />
```

Then it appends the Three.js renderer DOM element into that mount node:

```js
mount.appendChild(renderer.domElement);
```

### Cleanup Logic

On unmount, it cleans up:

- animation frame
- resize listener
- geometries
- materials
- renderer

This cleanup is part of the current behavior and should be preserved.

## 3. `src/MicrophoneSender.jsx`

### Role

This file provides the microphone input pipeline and is the source of the `audioLevel` used by the Three.js scene.

### Import

```js
import socket from "./socket/candidateSocket";
```

### Main Responsibilities

- requests microphone permission
- creates an `AudioContext`
- creates an `AnalyserNode`
- measures time-domain waveform energy each animation frame
- computes RMS audio level
- normalizes that level and sends it upward through `onAudioLevel`
- records audio chunks using `MediaRecorder`
- converts recorded audio into PCM int16
- base64-encodes audio chunks
- emits audio chunks to backend through socket
- registers the candidate role with backend

### Important Data Path

The exact voice-to-scene path is:

```text
MicrophoneSender.jsx
  -> onAudioLevel(normalizedLevel)
  -> CandidateApp.jsx setAudioLevel
  -> SpeakingScene.jsx receives audioLevel prop
  -> Three.js scene animation intensifies
```

### Socket Events Emitted

- `register_role`
- `join_session`
- `audio_chunk`

### Why This File Matters

This file is not optional if the clone must reproduce the same live reactive scene. The Three.js scene depends on the value produced here.

## 4. `src/WebcamSender.jsx`

### Role

This file captures webcam frames and sends them to the backend.

### Main Responsibilities

- requests camera permission
- starts a hidden live video stream
- copies video frames to a hidden canvas
- converts frames to JPEG data URLs
- POSTs one frame per second to the backend

### Backend Endpoint Used

```js
fetch("http://127.0.0.1:5000/video/analyze", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    session_id: sessionId,
    frame: frame,
  }),
})
```

### Wiring From Root

This is mounted inside `CandidateApp.jsx`:

```jsx
<WebcamSender sessionId={sessionId} onStatusChange={setCameraStatus} />
```

### Why This File Matters

Without this file, the clone will still render the page and the Three.js scene, but the candidate app will no longer send camera frames for analysis, so it will not match the current proctoring behavior.

## 5. `src/TabTracker.jsx`

### Role

This file monitors tab or window focus changes.

### Behavior

It listens for `window.blur` and emits a socket event when the user leaves the tab/window.

### Socket Event Emitted

```js
socket.emit("tab_switch", { session_id: sessionId });
```

### Wiring From Root

```jsx
<TabTracker sessionId={sessionId} />
```

### Why This File Matters

Without this file, the clone will lose the current tab-switch monitoring behavior.

## 6. `src/socket/candidateSocket.js`

### Role

This file creates the shared Socket.IO client connection used by the candidate-side components.

### Current Connection Target

```js
io("http://127.0.0.1:5000", {
  transports: ["websocket", "polling"],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 10,
  timeout: 20000,
  autoConnect: true,
});
```

### Used By

- `src/MicrophoneSender.jsx`
- `src/TabTracker.jsx`

### Why This File Matters

If the clone changes the import path or socket configuration, the current candidate-side behavior will not match exactly.

## 7. Styling Files

## `src/App.css`

This file defines the app's main visual layout.

It controls:

- full-screen page layout
- scene canvas positioning
- dark futuristic gradient background
- overlay gradients above the scene
- status card layout and appearance
- audio meter styling
- responsive layout behavior

The `.scene-canvas` class in this file is especially important because it gives the Three.js scene its full-screen absolute positioning.

## `src/index.css`

This file defines:

- body margin reset
- global font stack
- root minimum height
- page background color

Both CSS files are required to preserve the same visual result.

## Inactive But Present Files

The following files exist but are not part of the active startup chain for the current candidate scene:

- `src/App.jsx`
- `src/App.js`
- `src/App.test.js`
- `src/logo.svg`
- `src/socket.js`

### Important Note About `src/App.jsx`

`App.jsx` contains a router-based setup:

```jsx
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
```

However, this file is not currently used because `src/index.js` renders `CandidateApp` directly.

If you want the clone to behave exactly like the current app, do not replace the current `index.js` behavior with `App.jsx` unless you intentionally want routing.

## Required File List To Reproduce Current App

To recreate the same active candidate implementation, preserve this structure:

```text
frontend/candidate-app/
  package.json
  package-lock.json
  public/
    index.html
    favicon.ico
    logo192.png
    logo512.png
    manifest.json
    robots.txt
  src/
    index.js
    index.css
    CandidateApp.jsx
    SpeakingScene.jsx
    MicrophoneSender.jsx
    WebcamSender.jsx
    TabTracker.jsx
    App.css
    reportWebVitals.js
    setupTests.js
    socket/
      candidateSocket.js
```

Optional or currently inactive files:

```text
src/App.jsx
src/App.js
src/App.test.js
src/logo.svg
src/socket.js
```

## Backend Integration Requirements

To function exactly like the current app, the clone also needs a backend reachable at:

`http://127.0.0.1:5000`

### Socket Endpoint Usage

The frontend expects a Socket.IO backend that accepts:

- `register_role`
- `join_session`
- `audio_chunk`
- `tab_switch`

### HTTP Endpoint Usage

The frontend expects:

`POST /video/analyze`

### What Works Without Backend

If the backend is unavailable:

- the page still loads
- the Three.js scene still renders
- the audio-reactive animation can still work locally if microphone access is granted

But these backend-coupled features will fail:

- audio upload
- camera frame upload
- tab switch reporting
- session registration/join flow

## Exact Behavioral Summary

This is the current user-facing behavior of the candidate app:

1. The page loads a single candidate interview screen.
2. A Three.js animated space-like background is shown behind the UI.
3. Microphone access is requested.
4. Camera access is requested.
5. The candidate is registered and joined to the session over socket.
6. Audio energy is measured continuously.
7. The 3D globe scene responds to live speaking intensity.
8. A hidden webcam stream captures frames every second.
9. Frames are sent to backend for analysis.
10. Audio chunks are sent to backend over socket.
11. Leaving the browser tab emits a tab switch event.
12. The UI shows microphone state, camera state, and voice activity state.

## Exact Replication Instructions For A Clone

If you need another copy of this project to build the same candidate app, do the following:

1. Create or preserve the project at `frontend/candidate-app`.
2. Use Create React App with `react-scripts`.
3. Add the same dependencies from the current `package.json`, especially `three` and `socket.io-client`.
4. Ensure `public/index.html` contains `<div id="root"></div>`.
5. Make `src/index.js` import and render `CandidateApp` directly.
6. Recreate `src/CandidateApp.jsx` with the same imports and prop wiring.
7. Recreate `src/SpeakingScene.jsx` as the Three.js scene renderer.
8. Recreate `src/MicrophoneSender.jsx` so it computes `audioLevel` locally and emits audio chunks.
9. Recreate `src/WebcamSender.jsx` so it captures video frames and posts them to `/video/analyze`.
10. Recreate `src/TabTracker.jsx` so it emits `tab_switch` on window blur.
11. Recreate `src/socket/candidateSocket.js` pointing to `http://127.0.0.1:5000`.
12. Preserve `src/App.css` and `src/index.css` so the same UI layout and full-screen scene behavior are retained.
13. Run `npm install` and then `npm start`.

## Minimal Exact Link Map

If you only need the shortest accurate dependency summary, use this:

```text
index.html -> index.js -> CandidateApp.jsx -> SpeakingScene.jsx
                                      -> MicrophoneSender.jsx -> socket/candidateSocket.js
                                      -> WebcamSender.jsx
                                      -> TabTracker.jsx -> socket/candidateSocket.js
                                      -> App.css
index.js -> index.css
```

## Final Notes

- The active Three.js candidate app is in `frontend/candidate-app`, not `frontend_v2/candidate-app`.
- The current active root component is `CandidateApp.jsx`.
- The scene animation is coupled to live mic energy produced in `MicrophoneSender.jsx`.
- The clone must preserve both the React file links and the backend URL/event contracts to behave exactly the same.
