import { FC, useContext } from "react";
import {
  CssBaseline,
  ThemeProvider as MuiThemeProvider,
  createTheme,
} from "@mui/material";
import { ThemeProvider } from "./contexts/theme/index";
import HomePage from "./pages/HomePage";
import ConfigContext from "./contexts/config-context";
import { WebStorageStateStore, Log } from "oidc-client-ts";
import { AuthProvider } from "react-oidc-context";

// 启用详细日志，帮助调试
Log.setLogger(console);
Log.setLevel(Log.DEBUG);

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
    authority: config?.oidcIssuer,
    client_id: config?.oidcClientId,
    redirect_uri: config?.oidcRedirectUrl,
    scope: "openid email profile",
    loadUserInfo: true,

    // 修改存储配置
    stateStore: new WebStorageStateStore({
      store: window.localStorage,
    }),

    // 简化回调处理
    onSigninCallback: () => {
      // 移除 URL 中的认证参数
      const searchParams = new URLSearchParams(window.location.search);
      searchParams.delete("code");
      searchParams.delete("state");
      const newUrl = `${window.location.origin}${window.location.pathname}${
        searchParams.toString() ? "?" + searchParams.toString() : ""
      }`;
      window.history.replaceState({}, "", newUrl);
    },

    // 其他必要配置
    response_type: "code",
    response_mode: "query",
    automaticSilentRenew: true,
    revokeTokensOnSignout: true,

    // 登出配置
    post_logout_redirect_uri: window.location.origin,
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
