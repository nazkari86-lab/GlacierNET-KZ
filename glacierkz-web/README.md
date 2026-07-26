# GlacierNET-KZ web application

Next.js interface for verified local glacier results, scientific GeoTIFF
segmentation, model comparison, trends, datasets, reports, and monitoring.

## Recommended local start

From the repository root:

```bash
./scripts/start.sh
```

Open `http://localhost:8080/explore` to inspect and compare already downloaded
years without uploading imagery. The full service hub is available at
`http://localhost:8080/hub`.

## Frontend development

```bash
cd glacierkz-web
npm ci
npm run dev
```

The development UI defaults to `http://localhost:3000`. Set
`NEXT_PUBLIC_API_URL=http://localhost:8000` when the API runs separately. The
unified gateway uses an empty `NEXT_PUBLIC_API_URL` for same-origin requests.

## Quality checks

```bash
npm test
npm run lint
npm run build
npm run test:e2e
```

The upload workflow accepts scientific multi-band GeoTIFF input. PNG, JPEG,
screenshots, and phone photos are not valid substitutes for Sentinel-2 or
Landsat spectral data.
