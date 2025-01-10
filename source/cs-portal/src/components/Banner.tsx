import { FC, useState, useEffect } from "react";
import { Box, IconButton, Container, Typography, Button } from "@mui/material";
import {
  ChevronLeft as PrevIcon,
  ChevronRight as NextIcon,
  ArrowForward as ArrowIcon,
} from "@mui/icons-material";

const banners = [
  {
    id: 1,
    image:
      "https://images.unsplash.com/photo-1616348436168-de43ad0db179?auto=format&fit=crop&q=80&w=2662&ixlib=rb-4.0.3",
    title: "iPhone 15 Pro",
    subtitle: "强大的 A17 Pro 芯片",
    description: "现在购买即可享受24期免息",
    color: "from-blue-600/90 via-blue-900/90 to-transparent",
  },
  {
    id: 2,
    image:
      "https://images.unsplash.com/photo-1605236453806-6ff36851218e?auto=format&fit=crop&q=80&w=2664&ixlib=rb-4.0.3",
    title: "MacBook Pro",
    subtitle: "新款 M3 芯片",
    description: "预购享受教育优惠",
    color: "from-purple-600/90 via-purple-900/90 to-transparent",
  },
  {
    id: 3,
    image:
      "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&q=80&w=2660&ixlib=rb-4.0.3",
    title: "Vision Pro",
    subtitle: "突破空间限制",
    description: "预约体验，即可获得限定礼品",
    color: "from-indigo-600/90 via-indigo-900/90 to-transparent",
  },
];

const Banner: FC = () => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      nextSlide();
    }, 5000);

    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSlide]);

  const nextSlide = () => {
    if (isAnimating) return;
    setIsAnimating(true);
    setCurrentSlide((prev) => (prev + 1) % banners.length);
    setTimeout(() => setIsAnimating(false), 500);
  };

  const prevSlide = () => {
    if (isAnimating) return;
    setIsAnimating(true);
    setCurrentSlide((prev) => (prev - 1 + banners.length) % banners.length);
    setTimeout(() => setIsAnimating(false), 500);
  };

  return (
    <Box
      className="relative bg-gray-900"
      sx={{
        height: { xs: "300px", sm: "400px", md: "500px" },
      }}
    >
      <Box
        className="absolute inset-0 flex"
        sx={{
          transition: "transform 500ms ease-out",
          transform: `translateX(-${currentSlide * 100}%)`,
        }}
      >
        {banners.map((banner) => (
          <Box key={banner.id} className="relative flex-shrink-0 w-full h-full">
            <img
              src={banner.image}
              alt={banner.title}
              className="absolute inset-0 w-full h-full object-cover opacity-80"
            />

            <Box
              className={`absolute inset-0 bg-gradient-to-r ${banner.color}`}
            />

            <Container
              maxWidth="xl"
              className="relative h-full z-10"
              sx={{
                px: { xs: 2, sm: 3, md: 4 },
              }}
            >
              <Box className="h-full flex flex-col justify-center">
                <Box
                  className="max-w-xl space-y-6"
                  sx={{
                    opacity: isAnimating ? 0 : 1,
                    transform: isAnimating
                      ? "translateY(20px)"
                      : "translateY(0)",
                    transition: "all 500ms ease-out",
                  }}
                >
                  <Typography
                    variant="overline"
                    className="text-white/90 tracking-wider text-lg"
                  >
                    {banner.subtitle}
                  </Typography>
                  <Typography
                    variant="h1"
                    className="text-white font-bold tracking-tight text-6xl"
                  >
                    {banner.title}
                  </Typography>
                  <Typography variant="h4" className="text-white/80 font-light">
                    {banner.description}
                  </Typography>
                  <Button
                    variant="contained"
                    size="large"
                    endIcon={<ArrowIcon />}
                    className="mt-8 bg-white text-gray-900 hover:bg-gray-100 text-lg px-8 py-3"
                  >
                    立即购买
                  </Button>
                </Box>
              </Box>
            </Container>
          </Box>
        ))}
      </Box>

      <IconButton
        onClick={prevSlide}
        className="absolute left-8 top-1/2 -translate-y-1/2 bg-black/20 hover:bg-black/40 text-white w-12 h-12 z-20"
        disabled={isAnimating}
      >
        <PrevIcon />
      </IconButton>
      <IconButton
        onClick={nextSlide}
        className="absolute right-8 top-1/2 -translate-y-1/2 bg-black/20 hover:bg-black/40 text-white w-12 h-12 z-20"
        disabled={isAnimating}
      >
        <NextIcon />
      </IconButton>

      <Box className="absolute bottom-8 left-1/2 -translate-x-1/2 flex gap-3 z-20">
        {banners.map((_, index) => (
          <Box
            key={index}
            onClick={() => setCurrentSlide(index)}
            className={`h-2 rounded-full transition-all duration-300 cursor-pointer ${
              currentSlide === index
                ? "w-8 bg-white"
                : "w-2 bg-white/50 hover:bg-white/80"
            }`}
          />
        ))}
      </Box>
    </Box>
  );
};

export default Banner;
