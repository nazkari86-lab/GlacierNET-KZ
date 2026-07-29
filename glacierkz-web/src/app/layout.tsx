import type { Metadata } from "next";
import "./globals.css";
import ClientProviders from "./providers";
import JsonLd from "@/components/JsonLd";

export const metadata: Metadata = {
  title: "GlacierNET-KZ — Cryosphere Observation and Evidence OS",
  description: "Auditable observation planning, field inspections, and evidence management for glaciers and mountain lakes.",
  keywords: ["cryosphere", "observation planning", "field inspection", "evidence management", "glacier", "mountain lake", "Kazakhstan"],
  authors: [{ name: "GlacierNET-KZ Team" }],
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://github.com/nazkari86-lab/GlacierNET-KZ"),
  openGraph: {
    title: "GlacierNET-KZ — Cryosphere Observation and Evidence OS",
    description: "Observation prioritisation and auditable evidence workflows for cryosphere monitoring teams",
    type: "website",
    locale: "en_US",
    alternateLocale: ["ru_RU", "kk_KZ"],
    siteName: "GlacierNET-KZ",
  },
  twitter: {
    card: "summary_large_image",
    title: "GlacierNET-KZ",
    description: "Auditable cryosphere observation planning and evidence management",
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
    <html lang="en" className="h-full antialiased">
      <head>
        <JsonLd />
      </head>
      <body className="min-h-full font-sans">
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
