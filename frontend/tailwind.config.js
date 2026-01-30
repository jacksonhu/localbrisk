/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // LocalBrisk 设计规范 - "Clear & Float" 风格
        background: "#F5F5F7",
        card: "#FFFFFF",
        foreground: "#333333",
        primary: {
          DEFAULT: "#2563EB",
          foreground: "#FFFFFF",
        },
        secondary: {
          DEFAULT: "#64748B",
          foreground: "#FFFFFF",
        },
        muted: {
          DEFAULT: "#F1F5F9",
          foreground: "#64748B",
        },
        accent: {
          DEFAULT: "#F1F5F9",
          foreground: "#0F172A",
        },
        border: "#E2E8F0",
        input: "#E2E8F0",
        ring: "#2563EB",
      },
      borderRadius: {
        lg: "12px",
        md: "8px",
        sm: "6px",
      },
      fontFamily: {
        sans: ["Segoe UI", "Microsoft YaHei", "sans-serif"],
      },
      boxShadow: {
        float: "0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)",
        "float-lg": "0 4px 16px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)",
      },
    },
  },
  plugins: [],
};
