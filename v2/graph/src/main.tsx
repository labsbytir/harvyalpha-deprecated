import { createRoot } from "react-dom/client";
import { ThemeProvider } from "@mui/material/styles";
import App from "./App";
import theme from "./theme";

const root = document.getElementById("query-app");
if (root) {
  createRoot(root).render(
    <ThemeProvider theme={theme}>
      <App />
    </ThemeProvider>,
  );
}
