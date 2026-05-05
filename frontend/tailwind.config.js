/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        sand: "#f3efe6",
        coral: "#ef7d57",
        teal: "#0d5c63",
        navy: "#16324f",
        gold: "#d1a054",
      },
      boxShadow: {
        card: "0 18px 40px rgba(22, 50, 79, 0.12)",
      },
      fontFamily: {
        display: ["Georgia", "serif"],
        body: ["Trebuchet MS", "sans-serif"],
      },
    },
  },
  plugins: [],
};
