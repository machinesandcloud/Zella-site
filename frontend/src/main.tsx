import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import App from "./App";
import "./index.css";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#1f7a8c"
    },
    secondary: {
      main: "#f97316"
    },
    background: {
      default: "#f6f4ef",
      paper: "#ffffff"
    },
    text: {
      primary: "#1f2937",
      secondary: "#64748b"
    }
  },
  typography: {
    fontFamily: "Space Grotesk, system-ui, sans-serif"
  },
  shape: {
    borderRadius: 14
  }
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
