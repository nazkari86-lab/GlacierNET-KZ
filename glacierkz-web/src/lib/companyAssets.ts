export type CompanyAsset = {
  id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  createdAt: string;
  operator?: string;
  sourceLabel?: string;
  sourceUrl?: string;
  operatorSourceUrl?: string;
  isPublicExample?: boolean;
};

export const ALES_HPP2_EXAMPLE = {
  id: "public-example-ales-hpp2",
  name: "ГЭС‑2 Каскада Алматинских ГЭС",
  type: "ГЭС",
  latitude: 43.1134553,
  longitude: 76.9159527,
  createdAt: "2026-08-01T00:00:00.000Z",
  operator: "АО «АлЭС»",
  sourceLabel: "OpenStreetMap way/235606904",
  sourceUrl: "https://www.openstreetmap.org/way/235606904",
  operatorSourceUrl: "https://www.ales.kz/kaskad-ges/",
  isPublicExample: true,
} satisfies CompanyAsset;
