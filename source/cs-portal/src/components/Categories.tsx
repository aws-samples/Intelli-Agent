import { FC } from "react";
import { Box, Typography, Paper } from "@mui/material";
import {
  PhoneAndroid,
  Laptop,
  Watch,
  Headphones,
  Camera,
  TabletMac,
  SportsEsports,
  Speaker,
} from "@mui/icons-material";

const categories = [
  {
    id: 1,
    name: "手机数码",
    icon: <PhoneAndroid />,
    color: "from-blue-500 to-blue-600",
  },
  {
    id: 2,
    name: "电脑办公",
    icon: <Laptop />,
    color: "from-purple-500 to-purple-600",
  },
  {
    id: 3,
    name: "智能穿戴",
    icon: <Watch />,
    color: "from-green-500 to-green-600",
  },
  {
    id: 4,
    name: "耳机音频",
    icon: <Headphones />,
    color: "from-red-500 to-red-600",
  },
  {
    id: 5,
    name: "相机摄影",
    icon: <Camera />,
    color: "from-yellow-500 to-yellow-600",
  },
  {
    id: 6,
    name: "平板电脑",
    icon: <TabletMac />,
    color: "from-pink-500 to-pink-600",
  },
  {
    id: 7,
    name: "游戏娱乐",
    icon: <SportsEsports />,
    color: "from-indigo-500 to-indigo-600",
  },
  {
    id: 8,
    name: "智能音箱",
    icon: <Speaker />,
    color: "from-cyan-500 to-cyan-600",
  },
];

const Categories: FC = () => {
  return (
    <Box className="py-8">
      <Typography variant="h5" className="font-bold mb-6">
        商品分类
      </Typography>
      <Box className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">
        {categories.map((category) => (
          <Paper
            key={category.id}
            className="group cursor-pointer hover:shadow-lg transition-all duration-300 overflow-hidden"
            elevation={0}
          >
            <Box className="p-4 text-center">
              <Box
                className={`w-12 h-12 mx-auto rounded-xl bg-gradient-to-br ${category.color} text-white flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}
              >
                {category.icon}
              </Box>
              <Typography className="text-gray-700 group-hover:text-gray-900 transition-colors">
                {category.name}
              </Typography>
            </Box>
          </Paper>
        ))}
      </Box>
    </Box>
  );
};

export default Categories;
