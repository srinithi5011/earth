/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#10201a",
        paper: "#f7f8f3",
        moss: {
          50: "#f2f7f2",
          100: "#dcebe0",
          300: "#9dc6ac",
          500: "#4a8a63",
          600: "#387050",
          700: "#2b5940",
        },
        soil: {
          500: "#8a6a4a",
        },
        alert: "#b3542e",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
