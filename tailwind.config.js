/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        primary: {
          50: "#eef3fa", 100: "#d4e1f2", 200: "#a9c3e6", 300: "#7ea5d9",
          400: "#5387cd", 500: "#2869c0", 600: "#0B3C95", 700: "#09307a",
          800: "#07245f", 900: "#051844",
        },
        surface: {
          DEFAULT: "#FAFAFC",
          card: "#FFFFFF",
        },
        ink: {
          DEFAULT: "#1E2229",
          secondary: "#687182",
          muted: "#9CA3AF",
        },
        success: { bg: "#E6F4EA", text: "#137333", border: "#CEEAD6" },
        error: { bg: "#FCE8E6", text: "#C5221F", border: "#F5C6C2" },
        warning: { bg: "#FEF7E0", text: "#B06000", border: "#FDEAA8" },
        info: { bg: "#E8F0FE", text: "#1A56DB", border: "#C3D9FC" },
      },
    },
  },
  plugins: [],
};
