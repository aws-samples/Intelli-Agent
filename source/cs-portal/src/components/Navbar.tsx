import { FC, useState } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Badge,
  InputBase,
  Box,
  Container,
} from "@mui/material";
import {
  Search as SearchIcon,
  ShoppingCart as CartIcon,
  Person as UserIcon,
  Favorite as WishlistIcon,
} from "@mui/icons-material";
import { useAuth } from "react-oidc-context";
import { Logout as LogoutIcon } from "@mui/icons-material";
const Navbar: FC = () => {
  const [cartCount] = useState(0);
  const auth = useAuth();

  return (
    <AppBar position="sticky" className="bg-white shadow-sm">
      <Container maxWidth="xl">
        <Toolbar className="px-0 justify-between">
          <Typography variant="h5" className="text-gray-800 font-bold">
            ShopName
          </Typography>

          <Box className="flex-1 mx-12 max-w-2xl">
            <Box className="flex items-center bg-gray-100 hover:bg-gray-50 rounded-full px-4 py-2 transition-colors">
              <SearchIcon className="text-gray-400 mr-2" />
              <InputBase
                placeholder="搜索商品..."
                className="flex-1"
                sx={{ fontSize: "0.95rem" }}
              />
            </Box>
          </Box>

          <Box className="flex items-center gap-4">
            <IconButton className="text-gray-700 hover:bg-gray-50">
              <Badge badgeContent={0} color="error">
                <WishlistIcon />
              </Badge>
            </IconButton>
            <IconButton className="text-gray-700 hover:bg-gray-50">
              <Badge badgeContent={cartCount} color="error">
                <CartIcon />
              </Badge>
            </IconButton>
            {!auth.isAuthenticated ? (
              <Button
                onClick={() => auth.signinRedirect()}
                startIcon={<UserIcon />}
                className="text-gray-700 hover:bg-gray-50 normal-case"
              >
                登录
              </Button>
            ) : (
              <span className="text-gray-700  normal-case">
                {auth.user?.profile?.email}
                <Button
                  onClick={() => auth.signoutRedirect()}
                  startIcon={<LogoutIcon />}
                  className="text-gray-700 hover:bg-gray-50 normal-case ml-2"
                >
                  登出
                </Button>
              </span>
            )}
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Navbar;
