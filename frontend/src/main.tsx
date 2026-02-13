import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import App from "./App";
import "./index.css";

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#3fd0c9"
    },
    secondary: {
      main: "#f4c76f"
    },
    background: {
      default: "#0b0f17",
      paper: "rgba(16, 20, 30, 0.85)"
    },
    text: {
      primary: "#e8edf6",
      secondary: "#9aa6bd"
    },
    success: {
      main: "#33d17a"
    },
    error: {
      main: "#ff5c5c"
    }
  },
  typography: {
    fontFamily: "\"Sora\", \"Space Grotesk\", system-ui, sans-serif",
    h1: { fontFamily: "\"Space Grotesk\", \"Sora\", sans-serif", fontWeight: 600 },
    h2: { fontFamily: "\"Space Grotesk\", \"Sora\", sans-serif", fontWeight: 600 },
    h3: { fontFamily: "\"Space Grotesk\", \"Sora\", sans-serif", fontWeight: 600 },
    h4: { fontFamily: "\"Space Grotesk\", \"Sora\", sans-serif", fontWeight: 600 }
  },
  shape: {
    borderRadius: 18
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          background: "rgba(14, 18, 28, 0.72)",
          border: "1px solid rgba(255, 255, 255, 0.06)",
          backdropFilter: "blur(18px)",
          boxShadow: "0 20px 50px rgba(4, 8, 18, 0.35)"
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          borderRadius: 14,
          fontWeight: 600
        }
      }
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600
        }
      }
    }
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
