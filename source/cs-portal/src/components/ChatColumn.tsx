import { FC, useState } from "react";
import {
  Paper,
  Typography,
  TextField,
  IconButton,
  Avatar,
  Box,
} from "@mui/material";
import { Send as SendIcon, Person as PersonIcon } from "@mui/icons-material";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { useTheme } from "../contexts/ThemeContext";

interface Message {
  id: number;
  type: "user" | "bot";
  content: string;
}

const ChatColumn: FC = () => {
  const { isDarkMode } = useTheme();
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, type: "user", content: "你好，我需要帮助" },
    {
      id: 2,
      type: "bot",
      content: "您好！我很乐意帮助您。请问有什么可以协助您的？",
    },
  ]);
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim()) {
      setMessages([
        ...messages,
        { id: Date.now(), type: "user", content: input },
      ]);
      setInput("");
    }
  };

  return (
    <Paper className="h-full flex flex-col rounded-xl overflow-hidden">
      <Box
        className={`p-4 ${
          isDarkMode
            ? "bg-gradient-to-b from-gray-800/50 to-transparent shadow-md"
            : "bg-gradient-to-b from-white/50 to-transparent shadow-sm"
        }`}
      >
        <Typography variant="h6" className="font-medium">
          对话历史
        </Typography>
      </Box>
      <Box className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <Box
            key={message.id}
            className={`flex items-start gap-3 ${
              message.type === "user" ? "flex-row-reverse" : ""
            }`}
          >
            <Avatar
              className={`${
                message.type === "user"
                  ? "bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/30"
                  : isDarkMode
                  ? "bg-gradient-to-br from-green-500 to-green-600 shadow-lg shadow-green-500/30"
                  : "bg-gradient-to-br from-green-400 to-green-500 shadow-lg shadow-green-500/30"
              }`}
            >
              {message.type === "user" ? <PersonIcon /> : <SmartToyIcon />}
            </Avatar>
            <Paper
              elevation={0}
              className={`p-3 max-w-[80%] rounded-2xl shadow-lg ${
                message.type === "user"
                  ? isDarkMode
                    ? "bg-blue-600/20 shadow-blue-500/10"
                    : "bg-blue-50 shadow-blue-500/10"
                  : isDarkMode
                  ? "bg-gray-800/50 shadow-black/10"
                  : "bg-gray-50 shadow-black/5"
              }`}
            >
              <Typography>{message.content}</Typography>
            </Paper>
          </Box>
        ))}
      </Box>
      <Box
        className={`p-4 ${
          isDarkMode
            ? "bg-gradient-to-t from-gray-800/50 to-transparent shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]"
            : "bg-gradient-to-t from-white/50 to-transparent shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.03)]"
        } flex gap-2`}
      >
        <TextField
          fullWidth
          variant="outlined"
          placeholder="输入消息..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          multiline
          maxRows={4}
          className={`rounded-xl ${
            isDarkMode ? "bg-gray-800/50" : "bg-white/50"
          }`}
        />
        <IconButton
          color="primary"
          onClick={handleSend}
          className={`shrink-0 rounded-xl shadow-lg ${
            isDarkMode
              ? "bg-blue-600 hover:bg-blue-700 shadow-blue-500/30"
              : "bg-blue-500 hover:bg-blue-600 shadow-blue-500/30"
          } text-white`}
        >
          <SendIcon className="shrink-0" />
        </IconButton>
      </Box>
    </Paper>
  );
};

export default ChatColumn;
