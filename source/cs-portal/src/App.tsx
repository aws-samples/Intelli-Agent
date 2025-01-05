import { FC } from "react";
import {
  Box,
  CssBaseline,
  ThemeProvider as MuiThemeProvider,
  createTheme,
  IconButton,
  useMediaQuery,
} from "@mui/material";
import { Brightness4, Brightness7 } from "@mui/icons-material";
import ChatColumn from "./components/ChatColumn";
import DocumentColumn from "./components/DocumentColumn";
import CustomerInfoColumn from "./components/CustomerInfoColumn";
import { ThemeProvider, useTheme } from "./contexts/ThemeContext";

const AppContent: FC = () => {
  const { isDarkMode, toggleTheme } = useTheme();
  const isMobile = useMediaQuery("(max-width: 768px)");
  const isTablet = useMediaQuery("(max-width: 1024px)");

  const theme = createTheme({
    palette: {
      mode: isDarkMode ? "dark" : "light",
      background: {
        default: isDarkMode ? "#111827" : "#ffffff",
        paper: isDarkMode
          ? "rgba(17, 24, 39, 0.8)"
          : "rgba(255, 255, 255, 0.7)",
      },
      primary: {
        main: isDarkMode ? "#3B82F6" : "#2563eb",
      },
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    },
    components: {
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            backgroundColor: isDarkMode
              ? "rgba(17, 24, 39, 0.8)"
              : "rgba(255, 255, 255, 0.7)",
            backdropFilter: "blur(12px)",
            boxShadow: isDarkMode
              ? "0 8px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1)"
              : "0 8px 24px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.5)",
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            "& .MuiOutlinedInput-root": {
              "& fieldset": {
                border: "none",
                boxShadow: isDarkMode
                  ? "0 2px 8px rgba(0, 0, 0, 0.3), inset 0 1px 2px rgba(0, 0, 0, 0.2)"
                  : "0 2px 8px rgba(0, 0, 0, 0.05), inset 0 1px 2px rgba(0, 0, 0, 0.06)",
              },
            },
          },
        },
      },
    },
  });

  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="min-h-screen w-full">
        {/* 背景装饰 */}
        <div className="fixed inset-0 z-0">
          {isDarkMode ? (
            <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
              <div className="absolute inset-0 opacity-30">
                <div className="absolute w-[800px] h-[800px] -top-48 -left-48 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob" />
                <div className="absolute w-[600px] h-[600px] -top-24 left-1/4 bg-cyan-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000" />
                <div className="absolute w-[600px] h-[600px] top-1/4 right-1/4 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000" />
              </div>
            </div>
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-blue-100 to-white">
              <div className="absolute inset-0">
                <div className="absolute w-[800px] h-[800px] -top-48 -left-48 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob" />
                <div className="absolute w-[600px] h-[600px] -top-24 left-1/4 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob animation-delay-2000" />
                <div className="absolute w-[600px] h-[600px] top-1/4 right-1/4 bg-pink-200 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob animation-delay-4000" />
              </div>
            </div>
          )}
        </div>

        {/* 主题切换按钮 */}
        <Box className="fixed top-4 right-4 z-50">
          <IconButton
            onClick={toggleTheme}
            className={`
              ${
                isDarkMode
                  ? "bg-gray-800/50 text-blue-400"
                  : "bg-white/30 text-blue-600"
              }
              hover:scale-110 transform transition-all duration-300
              backdrop-blur-lg shadow-lg
              ${
                isDarkMode
                  ? "shadow-black/20"
                  : "shadow-blue-500/20 hover:shadow-blue-500/30"
              }
            `}
          >
            {isDarkMode ? <Brightness7 /> : <Brightness4 />}
          </IconButton>
        </Box>

        {/* 内容区域 */}
        <Box className="relative z-10 h-screen p-6 w-[100vw]">
          {isMobile ? (
            <Box className="h-full overflow-y-auto space-y-6">
              <ChatColumn />
              <DocumentColumn />
              <CustomerInfoColumn />
            </Box>
          ) : isTablet ? (
            <Box className="h-full grid grid-cols-9 gap-6">
              <Box className="col-span-3">
                <ChatColumn />
              </Box>
              <Box className="col-span-6 space-y-6 overflow-y-auto">
                <DocumentColumn />
                <CustomerInfoColumn />
              </Box>
            </Box>
          ) : (
            <Box className="h-full grid grid-cols-9 gap-6">
              <Box className="col-span-2">
                <ChatColumn />
              </Box>
              <Box className="col-span-4">
                <DocumentColumn />
              </Box>
              <Box className="col-span-3">
                <CustomerInfoColumn />
              </Box>
            </Box>
          )}
        </Box>
      </Box>
    </MuiThemeProvider>
  );
};

const App: FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;
