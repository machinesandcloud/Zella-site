import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import "./index.css";

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#2fe3cf",
      dark: "#18b9a8",
      light: "#5ff0de"
    },
    secondary: {
      main: "#f6c777",
      dark: "#d19b46",
      light: "#ffd69a"
    },
    background: {
      default: "#0a0f16",
      paper: "rgba(14, 18, 28, 0.86)"
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
    h1: { fontFamily: "\"Space Grotesk\", \"Sora\", sans-serif", fontWeight: 600, letterSpacing: "-0.02em" },
    h2: { fontFamily: "\"Space Grotesk\", \"Sora\", sans-serif", fontWeight: 600, letterSpacing: "-0.02em" },
    h3: { fontFamily: "\"Space Grotesk\", \"Sora\", sans-serif", fontWeight: 600, letterSpacing: "-0.02em" },
    h4: { fontFamily: "\"Space Grotesk\", \"Sora\", sans-serif", fontWeight: 600, letterSpacing: "-0.02em" },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    button: { fontWeight: 600, letterSpacing: "0.01em" }
  },
  shape: {
    borderRadius: 18
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundImage:
            "radial-gradient(circle at top, rgba(47, 227, 207, 0.18), transparent 40%), radial-gradient(circle at 15% 30%, rgba(246, 199, 119, 0.14), transparent 42%)"
        }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          background: "linear-gradient(145deg, rgba(18, 23, 35, 0.92), rgba(9, 12, 20, 0.7))",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          backdropFilter: "blur(18px)",
          boxShadow: "0 24px 60px rgba(4, 8, 18, 0.5)"
        }
      }
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "linear-gradient(160deg, rgba(18, 23, 35, 0.92), rgba(9, 12, 20, 0.76))"
        }
      }
    },
    MuiCardContent: {
      styleOverrides: {
        root: {
          padding: 24
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          borderRadius: 14,
          fontWeight: 600
        },
        containedPrimary: {
          backgroundImage: "linear-gradient(120deg, #2fe3cf, #66f2dc)",
          color: "#071218",
          boxShadow: "0 16px 28px rgba(25, 180, 168, 0.28)"
        },
        containedSecondary: {
          backgroundImage: "linear-gradient(120deg, #f6c777, #ffdca3)",
          color: "#1a1207",
          boxShadow: "0 16px 28px rgba(210, 152, 70, 0.25)"
        },
        outlined: {
          borderColor: "rgba(255,255,255,0.2)"
        }
      }
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          color: "#d7e2f3",
          backgroundColor: "rgba(255,255,255,0.04)"
        }
      }
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          border: "1px solid rgba(255,255,255,0.1)",
          backgroundColor: "rgba(255,255,255,0.05)"
        }
      }
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          height: 3,
          borderRadius: 999
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
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </ThemeProvider>
  </React.StrictMode>
);
