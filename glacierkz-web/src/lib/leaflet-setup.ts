/** Point Leaflet default icons at copied assets in /public/leaflet. Client-only. */
export function initLeafletIcons(): void {
  if (typeof window === "undefined") return;

  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const L = require("leaflet") as typeof import("leaflet");
  L.Icon.Default.mergeOptions({
    iconUrl: "/leaflet/marker-icon.png",
    iconRetinaUrl: "/leaflet/marker-icon-2x.png",
    shadowUrl: "/leaflet/marker-shadow.png",
  });
}
