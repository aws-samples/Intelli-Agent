import { FC } from "react";
import { Box, Typography, Grid } from "@mui/material";
import ProductCard from "./ProductCard";

const newProducts = [
  {
    id: 1,
    name: "Apple Vision Pro",
    price: 29999,
    image:
      "https://images.unsplash.com/photo-1622979135225-d2ba269cf1ac?auto=format&fit=crop&q=80&w=2670",
    discount: 98,
    rating: 5.0,
    reviews: 12,
  },
  {
    id: 2,
    name: "Apple Watch Series 9",
    price: 3299,
    image:
      "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?auto=format&fit=crop&q=80&w=2671",
    discount: 92,
    rating: 4.8,
    reviews: 45,
  },
  {
    id: 3,
    name: "HomePod mini",
    price: 749,
    image:
      "https://images.unsplash.com/photo-1589492477829-5e65395b66cc?auto=format&fit=crop&q=80&w=2671",
    discount: 90,
    rating: 4.6,
    reviews: 67,
  },
  {
    id: 4,
    name: "Magic Keyboard",
    price: 999,
    image:
      "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&q=80&w=2665",
    discount: 95,
    rating: 4.7,
    reviews: 89,
  },
];

const NewArrivals: FC = () => {
  return (
    <Box>
      <Box className="flex justify-between items-center mb-6">
        <Typography variant="h5" className="font-bold">
          新品上市
        </Typography>
        <Typography
          variant="body2"
          className="text-blue-600 cursor-pointer hover:underline"
        >
          查看更多 →
        </Typography>
      </Box>
      <Grid container spacing={3}>
        {newProducts.map((product) => (
          <Grid item key={product.id} xs={12} sm={6} md={3}>
            <ProductCard product={product} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default NewArrivals;
