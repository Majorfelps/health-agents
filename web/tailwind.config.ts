import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // WhatsApp-like palette
        wa: {
          green: "#25D366",
          "green-dark": "#075E54",
          teal: "#128C7E",
          "bubble-in": "#FFFFFF",
          "bubble-out": "#DCF8C6",
          bg: "#ECE5DD",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "Helvetica Neue", "Arial"],
      },
    },
  },
  plugins: [],
};
export default config;
