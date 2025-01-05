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
} from "@mui/material";
import {
  Inventory as ProductIcon,
  CalendarToday as DateIcon,
  LightbulbOutlined as TipIcon,
  Star as StarIcon,
} from "@mui/icons-material";
import { useTheme } from "../contexts/ThemeContext";

const CustomerInfoColumn: FC = () => {
  const { isDarkMode } = useTheme();

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
          客户信息
        </Typography>
      </Box>
      <Box className="flex-1 overflow-y-auto">
        <Box className="p-6">
          <Box
            className={`rounded-xl p-6 mb-6 ${
              isDarkMode
                ? "bg-gray-800/30 shadow-lg shadow-black/5"
                : "bg-white/50 shadow-lg shadow-black/5"
            }`}
          >
            <Box className="flex items-center gap-4 mb-6">
              <Avatar
                className={`w-16 h-16 ${
                  isDarkMode
                    ? "bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg shadow-blue-500/30"
                    : "bg-gradient-to-br from-blue-400 to-purple-500 shadow-lg shadow-blue-500/20"
                }`}
              >
                张
              </Avatar>
              <Box>
                <Typography variant="h6">张三</Typography>
                <Box className="flex gap-2 mt-2">
                  <Chip
                    size="small"
                    icon={<StarIcon className="text-yellow-500" />}
                    label="VIP客户"
                    className={`${
                      isDarkMode
                        ? "bg-yellow-500/10 text-yellow-500"
                        : "bg-yellow-100 text-yellow-700"
                    } shadow-sm`}
                  />
                  <Chip
                    size="small"
                    label="活跃用户"
                    className={`${
                      isDarkMode
                        ? "bg-green-500/10 text-green-500"
                        : "bg-green-100 text-green-700"
                    } shadow-sm`}
                  />
                </Box>
              </Box>
            </Box>
            <List>
              <ListItem>
                <ListItemIcon>
                  <Box
                    className={`p-2 rounded-lg ${
                      isDarkMode ? "bg-blue-600/10" : "bg-blue-50"
                    }`}
                  >
                    <ProductIcon className="text-blue-500" />
                  </Box>
                </ListItemIcon>
                <ListItemText
                  primary="产品型号"
                  secondary="Pro Max 2024"
                  secondaryTypographyProps={{
                    className: isDarkMode ? "text-gray-400" : "text-gray-600",
                  }}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Box
                    className={`p-2 rounded-lg ${
                      isDarkMode ? "bg-blue-600/10" : "bg-blue-50"
                    }`}
                  >
                    <DateIcon className="text-blue-500" />
                  </Box>
                </ListItemIcon>
                <ListItemText
                  primary="购买日期"
                  secondary="2024-03-15"
                  secondaryTypographyProps={{
                    className: isDarkMode ? "text-gray-400" : "text-gray-600",
                  }}
                />
              </ListItem>
            </List>
          </Box>

          <Box>
            <Typography variant="h6" className="font-medium mb-4">
              AI 建议
            </Typography>
            <Box className="space-y-3">
              {[
                "根据用户使用习惯，建议开启自动备份功能",
                "检测到系统性能有优化空间，建议更新到最新版本",
                "用户经常使用A功能，推荐开启快捷操作",
              ].map((tip, index) => (
                <Box
                  key={index}
                  className={`p-4 rounded-xl ${
                    isDarkMode
                      ? "bg-gradient-to-r from-blue-600/10 to-transparent shadow-lg shadow-black/5"
                      : "bg-gradient-to-r from-blue-50 to-transparent shadow-md shadow-black/5"
                  }`}
                >
                  <Box className="flex gap-3">
                    <Box
                      className={`p-2 rounded-lg shrink-0 ${
                        isDarkMode ? "bg-yellow-500/10" : "bg-yellow-50"
                      }`}
                    >
                      <TipIcon className="text-yellow-500" />
                    </Box>
                    <Typography
                      variant="body2"
                      className={isDarkMode ? "text-gray-300" : "text-gray-600"}
                    >
                      {tip}
                    </Typography>
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
