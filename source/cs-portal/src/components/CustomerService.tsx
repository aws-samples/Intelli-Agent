import { FC, useContext, useEffect, useState, useRef } from "react";
import {
  Box,
  Fab,
  Dialog,
  IconButton,
  Typography,
  TextField,
  Button,
  Paper,
  Avatar,
} from "@mui/material";
import {
  Close as CloseIcon,
  Send as SendIcon,
  SmartToy as RobotIcon,
} from "@mui/icons-material";
import useWebSocket, { ReadyState } from "react-use-websocket";
import { useAuth } from "react-oidc-context";
import ConfigContext from "../contexts/config-context";
import { v4 as uuidv4 } from "uuid";
import useAxiosWorkspaceRequest from "../assets/useAxiosWorkspaceRequest";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkHtml from "remark-html";

export interface ChatMessageType {
  messageId: string;
  role: "agent" | "user"; // Assuming "agent" and "user" are possible roles
  content: string;
  createTimestamp: string; // ISO 8601 string format
  additional_kwargs: Record<string, unknown>; // Assuming it can be any object
}

export interface ChatMessageResponse {
  Items: ChatMessageType[];
  Count: number;
}

const CustomerService: FC = () => {
  const auth = useAuth();
  const config = useContext(ConfigContext);
  const request = useAxiosWorkspaceRequest();
  const [sessionId] = useState(() => {
    const storedSessionId = localStorage.getItem("cs-sessionId");
    if (storedSessionId) {
      return storedSessionId;
    }
    const newSessionId = uuidv4();
    localStorage.setItem("cs-sessionId", newSessionId);
    return newSessionId;
  });
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      id: "1",
      type: "bot",
      content: "您好！我是智能客服助手，请问有什么可以帮您？",
    },
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { lastMessage, sendMessage, readyState } = useWebSocket(
    `${config?.workspaceWebsocket}?idToken=${auth.user?.id_token}&user_id=${auth.user?.profile?.sub}&session_id=${sessionId}&role=user`,
    {
      onOpen: () => console.log("opened"),
      shouldReconnect: () => true,
    }
  );

  const handleSend = () => {
    if (!message.trim()) return;

    const sendMessageObj = {
      query: message,
      entry_type: "common",
      session_id: sessionId,
      user_id: auth.user?.profile?.sub,
      action: "sendMessage",
    };
    sendMessage(JSON.stringify(sendMessageObj));
    setMessage("");
    setMessages((prev) => [
      ...prev,
      { id: uuidv4(), type: "user", content: message },
    ]);
  };

  const getMessageList = async () => {
    const response: ChatMessageResponse = await request({
      url: `/customer-sessions/${sessionId}/messages`,
      method: "get",
    });
    if (response.Items.length > 0) {
      const messages = response.Items.map((item) => ({
        id: item.messageId,
        type: item.role === "agent" ? "bot" : "user",
        content: item.content,
      }));
      setMessages(messages);
    } else {
      setMessages([
        {
          id: "1",
          type: "bot",
          content: "您好！我是智能客服助手，请问有什么可以帮您？",
        },
      ]);
    }
  };

  useEffect(() => {
    console.info("lastMessage", lastMessage);
    if (lastMessage && lastMessage.data) {
      const data = JSON.parse(lastMessage.data);
      console.info("data", data);
      setMessages((prev) => [
        ...prev,
        {
          id: data.message_id,
          type: "bot",
          content: data.query,
        },
      ]);
    }
  }, [lastMessage]);

  useEffect(() => {
    if (sessionId) {
      getMessageList();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    console.info("auth", auth);
  }, [auth]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <>
      <Fab
        color="primary"
        className="fixed right-8 bottom-8 z-50 group"
        onClick={() => setOpen(!open)}
        sx={{
          background: "linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)",
          "&:hover": {
            background: "linear-gradient(45deg, #2196F3 10%, #21CBF3 70%)",
          },
        }}
      >
        <Box className="relative">
          <RobotIcon className="text-white group-hover:scale-110 transition-transform" />
          <Box
            className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"
            sx={{ animation: "pulse 2s infinite" }}
          />
        </Box>
      </Fab>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            position: "fixed",
            bottom: 26,
            right: 32,
            m: 0,
            width: "480px",
            borderRadius: 2,
          },
        }}
      >
        <Box className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-blue-500 to-blue-400">
          <Box className="flex items-center gap-3">
            <Avatar
              sx={{
                background: "linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)",
                padding: "2px",
              }}
            >
              <RobotIcon />
            </Avatar>
            <Box>
              <Typography variant="h6" className="font-medium text-white">
                智能客服助手
              </Typography>
              <Typography variant="caption" className="text-blue-50">
                在线为您服务
              </Typography>
            </Box>
          </Box>
          <IconButton
            onClick={() => setOpen(false)}
            size="small"
            className="text-white"
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {auth.isAuthenticated ? (
          <>
            <Box className="h-[600px] overflow-y-auto p-4 space-y-4">
              {messages.map((msg) => (
                <Box
                  key={msg.id}
                  className={`flex items-start gap-2 ${
                    msg.type === "bot" ? "" : "justify-end"
                  }`}
                >
                  {msg.type === "bot" && (
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        background:
                          "linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)",
                      }}
                    >
                      <RobotIcon sx={{ fontSize: 20 }} />
                    </Avatar>
                  )}
                  <Paper
                    elevation={0}
                    className={`p-3 max-w-[80%] ${
                      msg.type === "bot"
                        ? "bg-gray-100"
                        : "bg-blue-500 text-white"
                    }`}
                  >
                    <ReactMarkdown
                      className="text-sm"
                      remarkPlugins={[remarkGfm, remarkHtml]}
                      components={{
                        p: ({ children }) => (
                          <span className="block">{children}</span>
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </Paper>
                </Box>
              ))}
              <div ref={messagesEndRef} />
            </Box>
            <Box className="p-4 border-t">
              <Box className="flex gap-2">
                <TextField
                  fullWidth
                  size="small"
                  placeholder="请输入您的问题..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSend()}
                />
                <Button
                  variant="contained"
                  onClick={handleSend}
                  disabled={!message.trim() || readyState !== ReadyState.OPEN}
                >
                  <SendIcon />
                </Button>
              </Box>
            </Box>
          </>
        ) : (
          <Box className="h-[400px] overflow-y-auto p-4 space-y-4 flex flex-col items-center justify-center">
            <Typography variant="body2">请先登录，再与客服对话</Typography>
            <Button variant="contained" onClick={() => auth.signinRedirect()}>
              登录
            </Button>
          </Box>
        )}
      </Dialog>

      <style>
        {`
          @keyframes pulse {
            0% {
              transform: scale(0.95);
              box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
            }
            
            70% {
              transform: scale(1);
              box-shadow: 0 0 0 6px rgba(59, 130, 246, 0);
            }
            
            100% {
              transform: scale(0.95);
              box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
            }
          }
        `}
      </style>
    </>
  );
};

export default CustomerService;
