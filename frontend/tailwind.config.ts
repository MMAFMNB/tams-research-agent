import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        tam: {
          "deep-blue": "#222F62",
          "light-blue": "#1A6DB6",
          turquoise: "#6CB9B6",
          "dark-carbon": "#0E1A24",
          "soft-carbon": "#B1B3B6",
          gray: "#4A4A4A",
          "light-bg": "#E8F0F8",
        },
      },
      fontFamily: {
        sans: ["Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
