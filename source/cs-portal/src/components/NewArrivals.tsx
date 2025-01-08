import { FC } from "react";
import { Box, Typography, Grid } from "@mui/material";
import ProductCard from "./ProductCard";

const newProducts = [
  {
    id: 1,
    name: "Apple Vision Pro",
    price: 29999,
    image: "https://via.placeholder.com/300",
    rating: 5.0,
    reviews: 12,
  },
  {
    id: 2,
    name: "Apple Watch Series 9",
    price: 3299,
    image: "https://via.placeholder.com/300",
    rating: 4.9,
    reviews: 45,
  },
  {
    id: 3,
    name: "HomePod mini",
    price: 749,
    image: "https://via.placeholder.com/300",
    rating: 4.8,
    reviews: 67,
  },
  {
    id: 4,
    name: "Magic Keyboard",
    price: 999,
    image: "https://via.placeholder.com/300",
    rating: 4.7,
    reviews: 89,
  },
  {
    id: 5,
    name: "AirTag",
    price: 229,
    image: "https://via.placeholder.com/300",
    rating: 4.6,
    reviews: 134,
  },
  {
    id: 6,
    name: "Apple Pencil (USB-C)",
    price: 899,
    image: "https://via.placeholder.com/300",
    rating: 4.8,
    reviews: 56,
  },
];

const NewArrivals: FC = () => {
  return (
    <Box>
      <Box className="flex justify-between items-center mb-6">
        <Box>
          <Typography variant="h5" className="font-bold">
            新品上市
          </Typography>
          <Typography variant="body2" className="text-gray-500 mt-1">
            发现最新上架的精选商品
          </Typography>
        </Box>
        <Typography
          variant="body2"
          className="text-blue-600 cursor-pointer hover:underline"
        >
          查看更多 →
        </Typography>
      </Box>
      <Grid container spacing={3}>
        {newProducts.map((product) => (
          <Grid item key={product.id} xs={12} sm={6} md={4} lg={2}>
            <ProductCard product={product} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default NewArrivals;
