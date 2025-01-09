import { FC, useContext } from "react";
import {
  CssBaseline,
  ThemeProvider as MuiThemeProvider,
  createTheme,
} from "@mui/material";
import { ThemeProvider } from "./contexts/theme/index";
import HomePage from "./pages/HomePage";
import ConfigContext from "./contexts/config-context";
import { WebStorageStateStore } from "oidc-client-ts";
import { AuthProvider } from "react-oidc-context";

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
  const config = useContext(ConfigContext);
  const oidcConfig = {
    userStore: new WebStorageStateStore({ store: window.localStorage }),
    scope: "openid email profile",
    automaticSilentRenew: true,
    authority: config?.oidcIssuer,
    client_id: config?.oidcClientId,
    redirect_uri: config?.oidcRedirectUrl,
  };

  return (
    <AuthProvider {...oidcConfig}>
      <ThemeProvider>
        <MuiThemeProvider theme={theme}>
          <CssBaseline />
          <HomePage />
        </MuiThemeProvider>
      </ThemeProvider>
    </AuthProvider>
  );
};

export default App;
