import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          purple: "#7c3aed",
          violet: "#6d28d9",
          cyan: "#06b6d4",
          gold: "#f59e0b",
          rose: "#f43f5e",
          emerald: "#10b981",
        },
        glass: {
          white: "rgba(255,255,255,0.05)",
          border: "rgba(255,255,255,0.08)",
          hover: "rgba(255,255,255,0.1)",
          strong: "rgba(255,255,255,0.15)",
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-mesh":
          "radial-gradient(at 40% 20%, hsla(260,80%,20%,1) 0px, transparent 50%), radial-gradient(at 80% 0%, hsla(220,80%,15%,1) 0px, transparent 50%), radial-gradient(at 0% 50%, hsla(280,70%,12%,1) 0px, transparent 50%), radial-gradient(at 80% 50%, hsla(240,60%,10%,1) 0px, transparent 50%), radial-gradient(at 0% 100%, hsla(260,80%,18%,1) 0px, transparent 50%)",
      },
      backdropBlur: {
        xs: "2px",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-in-out",
        "slide-up": "slideUp 0.4s ease-out",
        "slide-in-right": "slideInRight 0.3s ease-out",
        float: "float 6s ease-in-out infinite",
        "pulse-slow": "pulse 4s cubic-bezier(0.4,0,0.6,1) infinite",
        shimmer: "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(20px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)",
        "glass-hover": "0 16px 48px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.15)",
        glow: "0 0 30px rgba(124,58,237,0.3)",
        "glow-cyan": "0 0 30px rgba(6,182,212,0.3)",
        "glow-gold": "0 0 30px rgba(245,158,11,0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
