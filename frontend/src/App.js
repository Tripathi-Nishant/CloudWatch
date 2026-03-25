import React from "react";
import Dashboard from "./pages/Dashboard";

// Load IBM Plex Mono from Google Fonts
const link = document.createElement("link");
link.rel  = "stylesheet";
link.href = "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap";
document.head.appendChild(link);

export default function App() {
  return <Dashboard />;
}