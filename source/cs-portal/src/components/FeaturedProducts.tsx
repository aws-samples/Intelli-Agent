import { FC } from "react";
import { Box, Typography, Grid } from "@mui/material";
import ProductCard from "./ProductCard";

const featuredProducts = [
  {
    id: 1,
    name: "iPhone 15 Pro",
    price: 8999,
    image:
      "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&q=80&w=2670",
    discount: 95,
    rating: 4.8,
    reviews: 125,
  },
  {
    id: 2,
    name: "MacBook Pro M3",
    price: 14999,
    image:
      "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=2626",
    discount: 90,
    rating: 4.9,
    reviews: 89,
  },
  {
    id: 3,
    name: "AirPods Pro",
    price: 1999,
    image:
      "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&q=80&w=2660",
    discount: 85,
    rating: 4.7,
    reviews: 230,
  },
  {
    id: 4,
    name: "iPad Air",
    price: 4999,
    image:
      "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&q=80&w=2675",
    discount: 88,
    rating: 4.6,
    reviews: 156,
  },
];

const FeaturedProducts: FC = () => {
  return (
    <Box>
      <Box className="flex justify-between items-center mb-6">
        <Typography variant="h5" className="font-bold">
          热门推荐
        </Typography>
        <Typography
          variant="body2"
          className="text-blue-600 cursor-pointer hover:underline"
        >
          查看更多 →
        </Typography>
      </Box>
      <Grid container spacing={3}>
        {featuredProducts.map((product) => (
          <Grid item key={product.id} xs={12} sm={6} md={3}>
            <ProductCard product={product} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default FeaturedProducts;
