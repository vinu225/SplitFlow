import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono, Inter } from "next/font/google";
import "./globals.css";

const heading = Space_Grotesk({ subsets: ["latin"], weight: ["500", "700"], variable: "--font-heading" });
const mono = JetBrains_Mono({ subsets: ["latin"], weight: ["500", "700"], variable: "--font-mono" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "SplitFlow: contracts to payouts",
  description: "Turn sponsorship contracts into verified PayPal payouts (sandbox prototype).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${heading.variable} ${mono.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
