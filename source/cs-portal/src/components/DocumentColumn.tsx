import { FC, useState } from "react";
import {
  Paper,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Box,
  ListItemButton,
} from "@mui/material";
import {
  Description as DocIcon,
  Article as ArticleIcon,
} from "@mui/icons-material";
import { useTheme } from "../contexts/ThemeContext";

const documents = [
  {
    id: "guide",
    title: "使用指南",
    icon: <DocIcon className="text-blue-400" />,
    content: `
# 产品使用指南

## 1. 快速开始
- 登录系统
- 配置基本设置
- 开始使用

## 2. 核心功能
- 功能A的使用方法
- 功能B的使用技巧
- 功能C的最佳实践

## 3. 高级特性
- 自定义配置
- 性能优化
- 插件系统
    `,
  },
  {
    id: "faq",
    title: "常见问题",
    icon: <ArticleIcon className="text-blue-400" />,
    content: `
# 常见问题解答

## Q1: 如何重置密码？
按照以下步骤操作：
1. 点击登录页的"忘记密码"
2. 输入注册邮箱
3. 按照邮件提示完成重置

## Q2: 如何升级账户？
联系客服进行升级操作。

## Q3: 数据如何导出？
在设置页面中找到"数据管理"选项。
    `,
  },
];

const DocumentColumn: FC = () => {
  const { isDarkMode } = useTheme();
  const [selectedDoc, setSelectedDoc] = useState(documents[0]);

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
          参考文档
        </Typography>
      </Box>
      <Box className="grid grid-cols-3 h-full">
        <Box
          className={`${
            isDarkMode
              ? "bg-gray-800/30 shadow-[4px_0_16px_-4px_rgba(0,0,0,0.1)]"
              : "bg-white/30 shadow-[4px_0_16px_-4px_rgba(0,0,0,0.03)]"
          }`}
        >
          <List>
            {documents.map((doc) => (
              <ListItem key={doc.id} disablePadding>
                <ListItemButton
                  onClick={() => setSelectedDoc(doc)}
                  className={`
                    transition-all duration-200
                    ${
                      selectedDoc.id === doc.id
                        ? isDarkMode
                          ? "bg-blue-600/20 shadow-inner shadow-blue-500/10"
                          : "bg-blue-50 shadow-inner shadow-blue-500/5"
                        : "hover:bg-opacity-50"
                    }
                  `}
                >
                  <ListItemIcon>
                    <Box
                      className={`p-1 rounded-lg ${
                        selectedDoc.id === doc.id
                          ? isDarkMode
                            ? "bg-blue-600/10"
                            : "bg-blue-100/50"
                          : ""
                      }`}
                    >
                      {doc.icon}
                    </Box>
                  </ListItemIcon>
                  <ListItemText
                    primary={doc.title}
                    className={selectedDoc.id === doc.id ? "text-blue-500" : ""}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
        <Box className="col-span-2 p-6 overflow-y-auto">
          <Box
            className={`rounded-xl p-6 ${
              isDarkMode
                ? "bg-gray-800/30 shadow-inner shadow-black/5"
                : "bg-white/50 shadow-inner shadow-black/5"
            }`}
          >
            <Typography
              component="pre"
              className={`whitespace-pre-wrap font-mono text-sm ${
                isDarkMode ? "text-gray-300" : "text-gray-600"
              }`}
            >
              {selectedDoc.content}
            </Typography>
          </Box>
        </Box>
      </Box>
    </Paper>
  );
};

export default DocumentColumn;
