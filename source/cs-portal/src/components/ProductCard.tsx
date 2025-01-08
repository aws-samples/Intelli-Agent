import { FC } from "react";
import {
  Card,
  CardMedia,
  CardContent,
  Typography,
  Box,
  IconButton,
  Rating,
} from "@mui/material";
import {
  ShoppingCart as CartIcon,
  Favorite as HeartIcon,
} from "@mui/icons-material";

interface Product {
  id: number;
  name: string;
  price: number;
  image: string;
  discount?: number;
  rating: number;
  reviews: number;
}

interface Props {
  product: Product;
}

const ProductCard: FC<Props> = ({ product }) => {
  const discountedPrice = product.discount
    ? (product.price * product.discount) / 100
    : product.price;

  return (
    <Card className="group h-full hover:shadow-lg transition-shadow relative overflow-hidden">
      <Box className="relative">
        <CardMedia
          component="img"
          image={product.image}
          alt={product.name}
          className="aspect-square object-cover group-hover:scale-105 transition-transform"
        />
        {product.discount && (
          <Box className="absolute top-2 left-2 bg-red-500 text-white px-2 py-1 rounded-full text-sm">
            {100 - product.discount}% OFF
          </Box>
        )}
        <Box className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <IconButton className="bg-white hover:bg-gray-100 shadow-md">
            <HeartIcon className="text-gray-600" />
          </IconButton>
        </Box>
      </Box>

      <CardContent>
        <Typography
          variant="h6"
          className="font-medium text-gray-800 line-clamp-2 mb-1"
        >
          {product.name}
        </Typography>
        <Box className="flex items-center gap-2 mb-2">
          <Rating
            value={product.rating}
            precision={0.1}
            readOnly
            size="small"
          />
          <Typography variant="body2" className="text-gray-500">
            ({product.reviews})
          </Typography>
        </Box>
        <Box className="flex items-center justify-between">
          <Box>
            <Typography variant="h6" className="text-blue-600 font-bold">
              ¥{discountedPrice.toLocaleString()}
            </Typography>
            {product.discount && (
              <Typography
                variant="body2"
                className="text-gray-500 line-through"
              >
                ¥{product.price.toLocaleString()}
              </Typography>
            )}
          </Box>
          <IconButton color="primary" className="bg-blue-50 hover:bg-blue-100">
            <CartIcon />
          </IconButton>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ProductCard;
