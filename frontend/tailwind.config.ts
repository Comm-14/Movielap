import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#14091f",
        surface: "#221133",
        surfaceAlt: "#2e1845",
        accent: "#facc15",
        muted: "#c4b5fd",
      },
      boxShadow: {
        card: "0 20px 60px rgba(0, 0, 0, 0.35)",
      },
      backgroundImage: {
        spotlight:
          "radial-gradient(circle at top, rgba(250, 204, 21, 0.28), transparent 30%), radial-gradient(circle at bottom, rgba(168, 85, 247, 0.24), transparent 28%)",
      },
    },
  },
  plugins: [],
};

export default config;
