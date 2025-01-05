import { FC } from "react";
import {
  Paper,
  Typography,
  Box,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  Inventory as ProductIcon,
  CalendarToday as DateIcon,
  LightbulbOutlined as TipIcon,
  Star as StarIcon,
  ContentCopy as CopyIcon,
  Send as SendIcon,
} from "@mui/icons-material";
import { useTheme } from "../contexts/ThemeContext";

interface Props {
  onSendMessage?: (message: string) => void;
}

const CustomerInfoColumn: FC<Props> = ({ onSendMessage }) => {
  const { isDarkMode } = useTheme();

  const aiSuggestions = [
    `建议操作：开启自动备份功能
原因：根据您的使用习惯分析，经常处理重要文件
具体步骤：
1. 进入系统设置
2. 选择"备份与同步"
3. 开启"自动备份"选项
4. 设置备份周期为"每日"`,

    `建议操作：更新到最新版本
原因：检测到系统性能有优化空间
预期收益：
- 提升30%运行速度
- 修复已知bug
- 增加新功能支持
更新方式：点击设置-系统更新-立即更新`,

    `建议操作：开启A功能快捷操作
原因：您在过去一周内使用该功能超过50次
开启方法：
1. 打开快捷设置面板
2. 找到"常用功能"
3. 将A功能添加到快捷栏
完成后可通过快捷键Ctrl+A直接调用`,
  ];

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // 可以添加一个复制成功的提示
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  const handleSend = (text: string) => {
    onSendMessage?.(text);
  };

  return (
    <Paper className="h-full flex flex-col rounded-xl overflow-hidden">
      <Box
        className={`p-3 ${
          isDarkMode
            ? "bg-gradient-to-b from-gray-800/50 to-transparent shadow-md"
            : "bg-gradient-to-b from-white/50 to-transparent shadow-sm"
        }`}
      >
        <Typography variant="h6" className="font-medium">
          客户信息
        </Typography>
      </Box>
      <Box className="flex-1 overflow-y-auto">
        <Box className="p-3">
          <Box
            className={`rounded-xl p-3 ${
              isDarkMode
                ? "bg-gray-800/30 shadow-lg shadow-black/5"
                : "bg-white/50 shadow-lg shadow-black/5"
            }`}
          >
            <Box className="flex items-center gap-3">
              <Avatar
                className={`w-12 h-12 ${
                  isDarkMode
                    ? "bg-gradient-to-br from-blue-500 to-purple-600"
                    : "bg-gradient-to-br from-blue-400 to-purple-500"
                }`}
              >
                张
              </Avatar>
              <Box className="min-w-0 flex-1">
                <Typography variant="subtitle1" className="font-medium">
                  张三
                </Typography>
                <Box className="flex gap-1 mt-1">
                  <Chip
                    size="small"
                    icon={<StarIcon className="text-yellow-500" />}
                    label="VIP客户"
                    className={`${
                      isDarkMode
                        ? "bg-yellow-500/10 text-yellow-500"
                        : "bg-yellow-100 text-yellow-700"
                    }`}
                  />
                  <Chip
                    size="small"
                    label="活跃用户"
                    className={`${
                      isDarkMode
                        ? "bg-green-500/10 text-green-500"
                        : "bg-green-100 text-green-700"
                    }`}
                  />
                </Box>
              </Box>
            </Box>
            <List className="!p-0 mt-2">
              <ListItem className="!p-1">
                <ListItemIcon className="!min-w-[36px]">
                  <Box
                    className={`p-1.5 rounded-lg ${
                      isDarkMode ? "bg-blue-600/10" : "bg-blue-50"
                    }`}
                  >
                    <ProductIcon className="text-blue-500" />
                  </Box>
                </ListItemIcon>
                <ListItemText
                  primary="产品型号"
                  secondary="Pro Max 2024"
                  className="!my-0"
                />
              </ListItem>
              <ListItem className="!p-1">
                <ListItemIcon className="!min-w-[36px]">
                  <Box
                    className={`p-1.5 rounded-lg ${
                      isDarkMode ? "bg-blue-600/10" : "bg-blue-50"
                    }`}
                  >
                    <DateIcon className="text-blue-500" />
                  </Box>
                </ListItemIcon>
                <ListItemText
                  primary="购买日期"
                  secondary="2024-03-15"
                  className="!my-0"
                />
              </ListItem>
            </List>
          </Box>

          <Box className="mt-3">
            <Typography variant="h6" className="font-medium mb-2">
              AI 回复建议
            </Typography>
            <Box className="space-y-2">
              {aiSuggestions.map((suggestion, index) => (
                <Box
                  key={index}
                  className={`rounded-lg ${
                    isDarkMode
                      ? "bg-gradient-to-r from-blue-600/10 to-transparent"
                      : "bg-gradient-to-r from-blue-50 to-transparent"
                  }`}
                >
                  <Box className="flex items-start gap-2 p-2">
                    <Box
                      className={`p-1.5 rounded-lg shrink-0 mt-0.5 ${
                        isDarkMode ? "bg-yellow-500/10" : "bg-yellow-50"
                      }`}
                    >
                      <TipIcon className="text-yellow-500" />
                    </Box>
                    <Box className="flex-1 min-w-0">
                      <Typography
                        variant="body2"
                        className={`whitespace-pre-line ${
                          isDarkMode ? "text-gray-300" : "text-gray-600"
                        }`}
                      >
                        {suggestion}
                      </Typography>
                    </Box>
                    <Box className="flex flex-col gap-1 ml-2">
                      <Tooltip title="复制建议">
                        <IconButton
                          size="small"
                          onClick={() => handleCopy(suggestion)}
                          className={
                            isDarkMode ? "text-gray-400" : "text-gray-500"
                          }
                        >
                          <CopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="发送到聊天">
                        <IconButton
                          size="small"
                          onClick={() => handleSend(suggestion)}
                          className={
                            isDarkMode ? "text-gray-400" : "text-gray-500"
                          }
                        >
                          <SendIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
      </Box>
    </Paper>
  );
};

export default CustomerInfoColumn;
