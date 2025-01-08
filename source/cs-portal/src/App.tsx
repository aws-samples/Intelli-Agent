import { FC } from "react";
import {
  CssBaseline,
  ThemeProvider as MuiThemeProvider,
  createTheme,
} from "@mui/material";
import { ThemeProvider } from "./contexts/theme/index";
import HomePage from "./pages/HomePage";

const theme = createTheme({
  palette: {
    primary: {
      main: "#2563eb",
    },
    secondary: {
      main: "#f59e0b",
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          borderRadius: "8px",
        },
      },
    },
  },
});

const App: FC = () => {
  return (
    <ThemeProvider>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        <HomePage />
      </MuiThemeProvider>
    </ThemeProvider>
  );
};

export default App;
