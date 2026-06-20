import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "Savvy — Smart Financial Management",
  description: "AI-powered personal finance management system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="mesh-bg min-h-screen text-white antialiased">
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "rgba(15,10,30,0.95)",
              color: "white",
              border: "1px solid rgba(255,255,255,0.1)",
              backdropFilter: "blur(20px)",
              borderRadius: "12px",
              fontSize: "14px",
            },
            success: { iconTheme: { primary: "#10b981", secondary: "white" } },
            error: { iconTheme: { primary: "#f43f5e", secondary: "white" } },
          }}
        />
      </body>
    </html>
  );
}
