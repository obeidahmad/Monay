import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Manrope, served from our own origin (no third-party font request): the four
// weights the type tokens use.
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import "@fontsource/manrope/800.css";
import "./styles/global.css";

import { App } from "./App";

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root element");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
