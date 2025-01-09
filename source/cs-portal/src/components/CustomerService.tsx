import { FC, useEffect, useState } from "react";
import {
  Box,
  Fab,
  Dialog,
  IconButton,
  Typography,
  TextField,
  Button,
  Paper,
} from "@mui/material";
import {
  SupportAgent as AgentIcon,
  Close as CloseIcon,
  Send as SendIcon,
} from "@mui/icons-material";
import useWebSocket, { ReadyState } from "react-use-websocket";

const CustomerService: FC = () => {
  const userId = "e438f438-9021-708d-39a0-6ac2fb9a9ef3";
  const sessionId = "abc02cf2-b0e3-4305-9574-a2878af43c81";
  const idToken =
    "eyJraWQiOiJRdlE0ZlhCWlpacFIxd3QreVRRMDNcL2NEemRZSElJMlJuYmNhbDhFSG55ND0iLCJhbGciOiJSUzI1NiJ9.eyJhdF9oYXNoIjoiMVdzaUwxLXBKZkdEa3I0ZklQWVhpdyIsInN1YiI6ImU0MzhmNDM4LTkwMjEtNzA4ZC0zOWEwLTZhYzJmYjlhOWVmMyIsImNvZ25pdG86Z3JvdXBzIjpbIkFkbWluIl0sImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtZWFzdC0xLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMV9LOFpjanI2TUMiLCJjb2duaXRvOnVzZXJuYW1lIjoiZTQzOGY0MzgtOTAyMS03MDhkLTM5YTAtNmFjMmZiOWE5ZWYzIiwib3JpZ2luX2p0aSI6ImI3ZGQ1YmY5LWQzMjctNDMwMC04MzAxLWQ4ZDEzNzdmMzc5OCIsImF1ZCI6IjJkc2RjNzN2dDA5bjhrYWd0cmVsZm1udDJsIiwiZXZlbnRfaWQiOiI4NjEwZmY5Zi1kYjJjLTRhYjktODEyYi0wODdhMzVlZTcyMWMiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTczNjM5NDMwMywiZXhwIjoxNzM2NDgwNzAzLCJpYXQiOjE3MzYzOTQzMDMsImp0aSI6ImRjOWE1YmU4LTIxYmEtNDQ0ZS05ZDMxLWNkZDU3MjM2MGVlNSIsImVtYWlsIjoiYm9iQGFtYXpvbi5jb20ifQ.pIiUJ3_nPeCFhvURMtUWpoHvwKyFMSlkRgoYKWevHbaB9N5OgpCGSTtUFLH1BVrZziwcZPbGjAd0ceDnY4yXlYqHXFIkv-g0VuV7DtIAoWpDtRXqKnaRikQ-Kw8sHMLOYRO43SDLpxZqaAlwJgNH9hj3_o-OOI3i9ruzPhxPGx1_Sa16d7i2SGg4b67xv1uZ-hDAMzujof5P4Hiec76M34EqmKQXYdmEAMkY24XWZbPAdP6YY7F5fVWcDrY8bQi_m_BwHNzqTXf8pEVpZM8VqV-H7ias8rGBWHvRkc0la-Wm_zt2hbf3k1C9OXXhn9lkbZdRSKr5v5MPE2SWlxrodQ";
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "bot",
      content: "您好！我是智能客服助手，请问有什么可以帮您？",
    },
  ]);

  const { lastMessage, sendMessage, readyState } = useWebSocket(
    `wss://iuzdwf0x93.execute-api.us-east-1.amazonaws.com/prod/?idToken=${idToken}&user_id=${userId}&session_id=${sessionId}&role=user`,
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
      user_id: userId,
      action: "sendMessage",
    };
    sendMessage(JSON.stringify(sendMessageObj));
  };

  useEffect(() => {
    console.info("lastMessage", lastMessage);
    if (lastMessage && lastMessage.data) {
      const data = JSON.parse(lastMessage.data);
      console.info("data", data);
      setMessages((prev) => [...prev, data]);
    }
  }, [lastMessage]);

  return (
    <>
      <Fab
        color="primary"
        className="fixed right-8 bottom-8 z-50"
        onClick={() => setOpen(!open)}
      >
        <AgentIcon />
      </Fab>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            position: "fixed",
            bottom: 96,
            right: 32,
            m: 0,
            width: "400px",
            borderRadius: 2,
          },
        }}
      >
        <Box className="flex items-center justify-between p-4 border-b">
          <Typography variant="h6" className="font-medium">
            在线客服
          </Typography>
          <IconButton onClick={() => setOpen(false)} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        <Box className="h-[400px] overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <Box
              key={msg.id}
              className={`flex ${msg.type === "bot" ? "" : "justify-end"}`}
            >
              <Paper
                elevation={0}
                className={`p-3 max-w-[80%] ${
                  msg.type === "bot" ? "bg-gray-100" : "bg-blue-500 text-white"
                }`}
              >
                <Typography variant="body2">{msg.content}</Typography>
              </Paper>
            </Box>
          ))}
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
      </Dialog>
    </>
  );
};

export default CustomerService;
