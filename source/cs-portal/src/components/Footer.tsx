import { FC } from "react";
import {
  Box,
  Container,
  Grid,
  Typography,
  IconButton,
  Stack,
} from "@mui/material";
import {
  Facebook,
  Twitter,
  Instagram,
  YouTube,
  Phone,
  Mail,
  LocationOn,
} from "@mui/icons-material";

const footerLinks = [
  {
    title: "购物指南",
    links: ["新用户指南", "支付方式", "配送方式", "售后服务"],
  },
  {
    title: "会员中心",
    links: ["会员制度", "会员权益", "积分商城", "优惠券"],
  },
  {
    title: "关于我们",
    links: ["品牌故事", "企业文化", "招贤纳士", "联系我们"],
  },
  {
    title: "商业合作",
    links: ["商家入驻", "营销中心", "合作伙伴", "开放平台"],
  },
];

const Footer: FC = () => {
  return (
    <Box className="bg-gray-900 text-gray-300 mt-16">
      <Container maxWidth="lg" className="py-12">
        <Grid container spacing={8}>
          {/* 联系信息 */}
          <Grid item xs={12} md={4}>
            <Typography variant="h6" className="text-white font-bold mb-4">
              ShopName
            </Typography>
            <Stack spacing={2}>
              <Box className="flex items-center gap-2">
                <Phone className="text-gray-400" />
                <Typography>400-123-4567</Typography>
              </Box>
              <Box className="flex items-center gap-2">
                <Mail className="text-gray-400" />
                <Typography>support@shopname.com</Typography>
              </Box>
              <Box className="flex items-center gap-2">
                <LocationOn className="text-gray-400" />
                <Typography>北京市朝阳区xx大厦</Typography>
              </Box>
            </Stack>
            <Stack direction="row" spacing={1} className="mt-4">
              <IconButton
                className="text-gray-400 hover:text-white"
                size="small"
              >
                <Facebook />
              </IconButton>
              <IconButton
                className="text-gray-400 hover:text-white"
                size="small"
              >
                <Twitter />
              </IconButton>
              <IconButton
                className="text-gray-400 hover:text-white"
                size="small"
              >
                <Instagram />
              </IconButton>
              <IconButton
                className="text-gray-400 hover:text-white"
                size="small"
              >
                <YouTube />
              </IconButton>
            </Stack>
          </Grid>

          {/* 导航链接 */}
          {footerLinks.map((section) => (
            <Grid item xs={6} sm={3} md={2} key={section.title}>
              <Typography
                variant="subtitle1"
                className="text-white font-bold mb-4"
              >
                {section.title}
              </Typography>
              <Stack spacing={2}>
                {section.links.map((link) => (
                  <Typography
                    key={link}
                    variant="body2"
                    className="text-gray-400 hover:text-white cursor-pointer transition-colors"
                  >
                    {link}
                  </Typography>
                ))}
              </Stack>
            </Grid>
          ))}
        </Grid>

        {/* 版权信息 */}
        <Box className="border-t border-gray-800 mt-12 pt-8 text-center">
          <Typography variant="body2" className="text-gray-500">
            © 2024 ShopName. All rights reserved.
          </Typography>
          <Typography variant="caption" className="text-gray-600 block mt-1">
            京ICP备12345678号-1 | 京公网安备11010502030232号
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default Footer;
