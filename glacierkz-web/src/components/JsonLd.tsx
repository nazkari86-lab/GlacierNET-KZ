const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://github.com/nazkari86-lab/GlacierNET-KZ";

const structuredData = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "GlacierNET-KZ",
  applicationCategory: "ScientificApplication",
  applicationSubCategory: "Remote Sensing / Glaciology",
  operatingSystem: "Web",
  description:
    "Deep learning glacier segmentation and monitoring for Zailiysky Alatau, Kazakhstan using U-Net on Sentinel-2 and Landsat imagery.",
  url: SITE_URL,
  softwareVersion: "0.2.0",
  isAccessibleForFree: true,
  author: {
    "@type": "Person",
    name: "Dulat Nurlanuly",
  },
  citation: {
    "@type": "CreativeWork",
    name: "GlacierNET-KZ: Deep Learning Glacier Monitoring for Kazakhstan",
    url: SITE_URL,
  },
  areaServed: {
    "@type": "Place",
    name: "Ili Alatau, Kazakhstan",
    geo: {
      "@type": "GeoCoordinates",
      latitude: 43.0,
      longitude: 77.0,
    },
  },
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
  featureList: [
    "U-Net glacier segmentation",
    "Multi-year trend analysis",
    "Forecast to 2050",
    "Sentinel-2 and Landsat support",
    "EN/RU/KK localization",
  ],
  inLanguage: ["en", "ru", "kk"],
  keywords: "glacier, remote sensing, U-Net, Sentinel-2, Landsat, Kazakhstan, climate change",
};

export default function JsonLd() {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}
