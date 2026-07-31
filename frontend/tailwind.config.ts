import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f7f3ee",
        charcoal: "#23211f",
        accent: "#c17a5a",
      },
    },
  },
  plugins: [],
};

export default config;
