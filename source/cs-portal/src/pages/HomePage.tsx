import { FC } from "react";
import { Container, Box } from "@mui/material";
import Banner from "../components/Banner";
import Categories from "../components/Categories";
import FeaturedProducts from "../components/FeaturedProducts";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import NewArrivals from "../components/NewArrivals";
import CustomerService from "../components/CustomerService";

const HomePage: FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <Box
        className="w-full"
        sx={{
          mt: { xs: 2, sm: 3, md: 4 },
        }}
      >
        <Banner />
      </Box>
      <Container
        maxWidth="xl"
        className="py-8 space-y-12"
        sx={{
          px: { xs: 2, sm: 3, md: 4 },
          mx: "auto",
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        <Categories />
        <FeaturedProducts />
        <NewArrivals />
      </Container>
      <Footer />
      <CustomerService />
    </div>
  );
};

export default HomePage;
