# GlacierNET-KZ Project Readiness Max Plan

Дата аудита: 2026-07-08

Цель: довести GlacierNET-KZ до максимально сильной публичной версии для open-source пользователей, climate-tech programs, research partners и B2G/B2B пилотов. 100% гарантии отбора невозможны, но этот план закрывает основные причины отказа: слабый рынок, нет пилота, нет покупателя, спорная научная валидация, непонятная бизнес-модель.

## Текущая сильная база

- Реальные raw-данные уже локально:
  - Sentinel-2: 2015-2024
  - Landsat: 2000, 2003, 2005, 2008, 2010, 2013
- `results/data_quality_report.json`: `ok=true`
- STAC и inventory есть:
  - `results/stac/catalog.json`
  - `results/tables/data_inventory.csv`
- Модели и метрики:
  - U-Net F1 0.8763, IoU 0.7798
  - Random Forest F1 0.8525
  - NDSI F1 0.8513
- Product surface:
  - Next.js dashboard
  - FastAPI backend
  - MCP server
  - HuggingFace/Gradio structure
- Проверки на 2026-06-28/2026-07-08:
  - web lint/test/build clean
  - root tests green
  - API tests green

## Главная стратегическая позиция

Нельзя подавать проект как просто "U-Net для ледников".

Подавать нужно так:

> GlacierNET-KZ is an AI climate-risk intelligence platform for Kazakhstan that turns satellite imagery into annual glacier maps, water-risk indicators, forecasts, and decision dashboards for government, infrastructure, ESG, and climate-adaptation planning.

## Почему не 100% прямо сейчас

1. Нет подтвержденного клиента или пилота.
2. Нет LOI от госоргана, университета, института или water/climate organization.
3. The capped 2016-2024 temporal benchmark now has a reportable untouched-2024 result (`Dice=0.7802`, `IoU=0.7382`), but it remains limited to one AOI and RGI-derived masks; external/cross-region validation is still required.
4. 2015 Sentinel-2 is a late-year TOA fallback and must be separated from strict summer SR analysis.
5. Business model needs sharper buyer, pricing, procurement path, and pilot scope.
6. Scientific story has outlier years and must distinguish climate signal from data/season/cloud artifacts.

## 30-дневный план до near-decision-ready

### Week 1: Scientific credibility

- Rebuild or clearly label the final trend table with data-source flags:
  - `landsat_historical`
  - `sentinel2_sr`
  - `sentinel2_toa_fallback`
- Exclude or visually mark 2015 from strict Sentinel summer trend.
- Add uncertainty/confidence layer to outputs:
  - model uncertainty
  - data quality score per year
  - cloud/season caveat per year
- Done: add RF feature importance plot and table.
- Done: add a capped multi-year Sentinel-2 patch dataset for 2016-2024, excluding 2015 by default.
- Done: add a strict 2023/2024 held-out-year evaluation path. Remaining: scale the dataset and obtain a converged temporal benchmark.

### Week 2: Product and demo

- Build a public demo flow:
  1. Open dashboard.
  2. Select Tuyuksu/Bogdanovich.
  3. Show 2000-2024 glacier area history.
  4. Show uncertainty and outlier explanation.
  5. Generate PDF decision report.
  6. Ask MCP/AI: "What years are high risk and why?"
- Add "Decision Report" export:
  - key maps
  - area table
  - trend + p-value + 95% CI
  - water-supply impact
  - caveats
- Add one public demo dataset small enough to run online without 15+ GB raw rasters.
- Add a landing/pitch page inside dashboard: problem, users, impact, demo.

### Week 3: Market validation

- Contact at least 15 relevant organizations.
- Target minimum evidence:
  - 3 discovery calls
  - 2 written emails confirming problem relevance
  - 1 LOI or pilot-interest letter
- Priority contacts:
  - Kazhydromet
  - Institute of Geography and Water Security
  - Al-Farabi KazNU geography/climate faculty
  - Almaty Akimat/environment/water departments
  - Ministry of Water Resources and Irrigation
  - Central Asian climate/water NGOs
  - UNDP Kazakhstan climate adaptation contacts
- Prepare a one-page pilot proposal:
  - 8-week pilot
  - study area: Ili Alatau / Tuyuksu / Bogdanovich
  - deliverables: dashboard + annual report + API + training
  - success metrics: report time reduction, validation accuracy, stakeholder usability

### Week 4: Project evidence package

- Prepare 10-slide pitch deck:
  1. Title and one-line value
  2. Problem: water security and glacier retreat
  3. Current pain: slow manual monitoring, fragmented data
  4. Solution: AI satellite monitoring platform
  5. Demo screenshots
  6. Model/data validation
  7. Customer/pilot evidence
  8. Business model
  9. Roadmap and scaling to Central Asia
  10. Ask: pilot, expert validation, partnership or funding
- Prepare 90-second demo video.
- Prepare one-page executive summary.
- Prepare technical appendix:
  - data provenance
  - model metrics
  - validation
  - limitations
  - reproducibility

## Business model to present

Primary model: B2G/B2B annual monitoring subscription.

- Government/regional agencies:
  - annual dashboard + reports
  - custom AOI monitoring
  - decision briefings
- Research institutions:
  - reproducible data products
  - model/API access
- Infrastructure/ESG:
  - climate-risk reporting
  - hydrological risk indicators

Suggested pilot pricing:

- Free/low-cost academic pilot: 0-1M KZT for validation and references.
- Government/NGO pilot: 3-8M KZT for one region and annual report.
- Full annual monitoring: 10-30M KZT/year depending on coverage and support.

## Program Scoring Strategy

### Astana Hub / AI'preneurs

What they reward:

- AI-based product
- MVP, not just idea
- rapid hypothesis testing
- customer discovery
- team capability
- investment or pilot potential

Project fit now: strong AI/MVP, weak traction.

To maximize:

- show dashboard live
- show API/MCP live
- show real data quality
- show 3 customer interviews
- show 1 LOI
- show clear 8-week pilot

### Astana Hub Ventures

What they reward:

- high-growth tech startup
- scalable market
- team and traction
- path to venture-scale returns

Project fit now: medium.

To maximize:

- position as climate intelligence SaaS for Central Asia, not just Kazakhstan
- show expansion to Kyrgyzstan, Tajikistan, Uzbekistan glacier basins
- show paid pilot path
- show annual recurring revenue model

### Scientific And Climate Programs

What they reward:

- measurable climate impact
- reproducible methodology
- open data/science
- stakeholder relevance

Project fit now: strong.

To maximize:

- strengthen uncertainty and validation
- get institutional advisor
- make methodology publication-grade
- separate caveats from claims

## Highest-impact technical improvements

1. Multi-year training dataset:
   - build patches for 2016-2024
   - exclude 2015 from training by default
   - train/val/test split by year or glacier region

2. Annual data quality scoring:
   - cloud/season/scene-count score
   - source type
   - confidence category

3. Uncertainty map:
   - MC dropout or ensemble disagreement
   - shown in dashboard and exported report

4. Decision report export:
   - PDF/HTML report for non-technical users

5. Pilot mode:
   - one command to run demo with small sample data
   - `scripts/start.sh` opens complete product story

6. Stakeholder-ready UI:
   - fewer technical panels by default
   - more decision cards:
     - area loss
     - high-risk years
     - confidence
     - water-supply implication
     - recommended action

## Things To Avoid In Public Pitch

- Do not overclaim "100% accurate glacier monitoring".
- Do not show 2015 as normal Sentinel summer SR.
- Do not lead with MCP, U-Net++, or backend architecture.
- Do not pitch only to investors before having a pilot.
- Do not present huge raw data size as a strength; present reproducible derived outputs.

## Near-100% readiness definition

The project is near-decision-ready when these are true:

- Live demo works in under 3 minutes.
- One PDF decision report is generated from dashboard.
- One cleaned scientific result table excludes/marks caveat years.
- One uncertainty/confidence layer is visible.
- At least 3 stakeholder interviews are documented.
- At least 1 LOI or pilot-interest email exists.
- Pitch deck, one-pager, and 90-second demo video are ready.
- All tests pass.

## Next immediate tasks

1. Done: create cleaned `results/tables/decision_ready_area_timeseries.csv`.
2. Done: add `results/tables/year_quality_scores.csv`.
3. Done: add dashboard cards for quality/confidence and stakeholder report export.
4. Build 2016-2024 multi-year patch dataset with disk-safe limits.
5. Done: draft 15 outreach targets/emails and add `docs/stakeholder_outreach_tracker.csv`.
6. Create pitch deck and one-page pilot proposal.
7. Done: add `scripts/build_project_evidence_package.py` to rebuild data quality, inventory and decision-ready tables in one command.
