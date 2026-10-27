import { createTheme } from "@mui/material/styles";

export const MONO = 'ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace';

// OpenCode-style dark theme (opencode.dev tokens)
const theme = createTheme({
  palette: {
    mode: "dark",
    background: { default: "#09090b", paper: "#121214" },
    primary: { main: "#f4f4f5", contrastText: "#09090b" },
    secondary: { main: "#a1a1aa" },
    success: { main: "#22c55e" },
    warning: { main: "#f59e0b" },
    error: { main: "#ef4444" },
    divider: "#27272a",
    text: { primary: "#f4f4f5", secondary: "#a1a1aa" },
    action: {
      hover: "rgba(255, 255, 255, 0.04)",
      selected: "rgba(255, 255, 255, 0.08)",
    },
  },
  typography: {
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", "Geist", "Inter", sans-serif',
    h6: { fontFamily: MONO, fontSize: "0.8rem", letterSpacing: "0.06em", fontWeight: 600 },
  },
  shape: { borderRadius: 6 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: "#121214",
          borderColor: "#27272a",
          backgroundImage: "none",
          boxShadow: "none",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 500,
          borderRadius: 6,
          boxShadow: "none",
          "&:hover": {
            boxShadow: "none",
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: "#09090b",
          "& fieldset": {
            borderColor: "#27272a",
          },
          "&:hover fieldset": {
            borderColor: "#3f3f46",
          },
          "&.Mui-focused fieldset": {
            borderColor: "#f4f4f5",
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderColor: "#27272a",
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: "#27272a",
        },
      },
    },
  },
});

export default theme;
