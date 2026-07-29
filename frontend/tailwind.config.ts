import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        blush: "#e8b4bc",
        sage: "#9caf88",
        ink: "#2d2a32",
      },
    },
  },
  plugins: [],
};

export default config;
