import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import ClientProviders from "./providers";
import JsonLd from "@/components/JsonLd";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "GlacierNET-KZ — Glacier Segmentation",
  description: "Geospatial AI glacier segmentation and monitoring for Zailiysky Alatau, Kazakhstan. Sentinel-2 + Landsat + U-Net.",
  keywords: ["glacier", "segmentation", "remote sensing", "Sentinel-2", "Landsat", "U-Net", "Kazakhstan", "Zailiysky Alatau", "climate change"],
  authors: [{ name: "GlacierNET-KZ Team" }],
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://github.com/nazkari86-lab/GlacierNET-KZ"),
  openGraph: {
    title: "GlacierNET-KZ — AI Glacier Monitoring",
    description: "Geospatial AI glacier segmentation and monitoring for Zailiysky Alatau, Kazakhstan",
    type: "website",
    locale: "en_US",
    alternateLocale: ["ru_RU", "kk_KZ"],
    siteName: "GlacierNET-KZ",
  },
  twitter: {
    card: "summary_large_image",
    title: "GlacierNET-KZ",
    description: "AI-powered glacier monitoring for Kazakhstan using U-Net on Sentinel-2 imagery",
  },
  alternates: {
    canonical: "/",
    languages: {
      en: "/",
      ru: "/",
      kk: "/",
    },
  },
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <head>
        <JsonLd />
      </head>
      <body className="min-h-full font-sans">
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
