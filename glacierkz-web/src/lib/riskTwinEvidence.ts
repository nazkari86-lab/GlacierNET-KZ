import type { GlacierRecord, RiskTwinObservationInput, RiskTwinSpatialContext, YearMapLayer } from "@/lib/api";

export type EvidenceKind = "glacier" | "annual_segmentation" | "lake" | "river" | "basin" | "historical_record" | "asset";
export type EvidenceMaturity = "inventory_reference" | "local_artifact" | "spatial_context" | "archive_record" | "planning_context" | "requires_verification";
export type DecisionImpact = "high" | "medium" | "low";

export interface EvidenceMapObject {
  id: string;
  kind: EvidenceKind;
  name: string;
  geometry: GeoJSON.GeoJsonObject;
  source: string;
  temporalCoverage: string;
  maturity: EvidenceMaturity;
  visibleFact: string;
  allowedClaim: string;
  prohibitedClaim: string;
  inspectorFacts: Array<{ label: string; value: string }>;
}

export interface EvidenceIssue {
  id: string;
  objectId?: string;
  decisionImpact: DecisionImpact;
  title: string;
  rationale: string;
  nextAction: string;
  blockedClaim: string;
}

type RankedAction = {
  action_id?: string;
  label?: string;
  target_variables?: string[];
  available?: boolean;
};

type FeatureLike = {
  geometry?: unknown;
  properties?: Record<string, unknown>;
};

const PROXIMITY_LIMIT = "Пространственная близость не доказывает причинную связь, путь потока, затопление или последствия.";
const GAP_DEFINITIONS: Record<string, Omit<EvidenceIssue, "id">> = {
  lake_area_m2: {
    decisionImpact: "medium",
    title: "Площадь озера требует проверки",
    rationale: "Инвентарный контур не заменяет измерение текущего состояния или объёма.",
    nextAction: "Получить чистую спутниковую сцену и проверить контур воды.",
    blockedClaim: "Нельзя утверждать изменение объёма или опасность по одному контуру.",
  },
  water_level_m: {
    decisionImpact: "high",
    title: "Уровень воды не измерен",
    rationale: "Без уровня нельзя сравнивать сценарии наблюдения и подготовки.",
    nextAction: "Измерить уровень воды с документированным временем и погрешностью.",
    blockedClaim: "Нельзя утверждать переполнение или вероятность события.",
  },
  freeboard_m: {
    decisionImpact: "high",
    title: "Свободный борт не измерен",
    rationale: "Геометрия свободного борта может исключить или допустить дальнейшую проверку сценариев.",
    nextAction: "Провести полевой профиль или съёмку БПЛА с указанной точностью.",
    blockedClaim: "Нельзя сравнивать сценарии переполнения.",
  },
  dam_stability_index: {
    decisionImpact: "high",
    title: "Состояние естественной преграды не подтверждено",
    rationale: "Карта и спутниковая текстура не заменяют инженерную или полевую оценку.",
    nextAction: "Запросить полевую оценку с источником, датой и методикой.",
    blockedClaim: "Нельзя заявлять устойчивость или неустойчивость преграды.",
  },
  outlet_capacity_fraction: {
    decisionImpact: "high",
    title: "Пропускная способность выпуска не подтверждена",
    rationale: "Этот пробел меняет допустимость исследований выпуска, мониторинга и подготовки.",
    nextAction: "Снять геометрию выпуска и канала в поле или с БПЛА.",
    blockedClaim: "Нельзя сравнивать сценарии понижения уровня или прорыва.",
  },
  channel_capacity_m3_s: {
    decisionImpact: "high",
    title: "Пропускная способность русла не измерена",
    rationale: "HydroRIVERS показывает справочный сегмент, а не локальную гидравлическую ёмкость.",
    nextAction: "Провести геодезическую съёмку сечений русла и задокументировать метод.",
    blockedClaim: "Нельзя строить маршрут или глубину распространения потока.",
  },
  exposed_asset_count: {
    decisionImpact: "medium",
    title: "Экспозиция объектов не подтверждена",
    rationale: "OSM и GHSL дают планировочный контекст, но не назначение, занятость или воздействие.",
    nextAction: "Проверить назначение критичных объектов и локальный реестр экспозиции.",
    blockedClaim: "Нельзя называть число затронутых людей или объектов.",
  },
};

function asGeometry(value: unknown): GeoJSON.GeoJsonObject | null {
  if (!value || typeof value !== "object") return null;
  const maybeGeometry = value as { type?: unknown };
  return typeof maybeGeometry.type === "string" ? value as GeoJSON.GeoJsonObject : null;
}

function sourceValue(value: unknown): string {
  return value === null || value === undefined || value === "" ? "not supplied" : String(value);
}

function featureObjects(
  features: FeatureLike[],
  kind: Exclude<EvidenceKind, "glacier" | "annual_segmentation">,
  source: string,
  temporalCoverage: string,
  makeName: (properties: Record<string, unknown>) => string,
  makeFacts: (properties: Record<string, unknown>) => Array<{ label: string; value: string }>,
  maturity: EvidenceMaturity,
  visibleFact: string,
  allowedClaim: string,
  prohibitedClaim = PROXIMITY_LIMIT,
): EvidenceMapObject[] {
  return features.flatMap((feature, index) => {
    const geometry = asGeometry(feature.geometry);
    if (!geometry) return [];
    const properties = feature.properties ?? {};
    const sourceId = sourceValue(properties.lake_id ?? properties.hyriv_id ?? properties.hybas_id ?? properties.event_id ?? properties.osm_id ?? properties.id ?? index + 1);
    return [{
      id: `${kind}:${sourceId}`,
      kind,
      name: makeName(properties),
      geometry,
      source,
      temporalCoverage,
      maturity,
      visibleFact,
      allowedClaim,
      prohibitedClaim,
      inspectorFacts: makeFacts(properties),
    }];
  });
}

function annualGeometry(layer: YearMapLayer): GeoJSON.Polygon {
  const [[south, west], [north, east]] = layer.bounds;
  return {
    type: "Polygon",
    coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
  };
}

export function buildEvidenceMapObjects(
  glacier: GlacierRecord | null,
  yearLayer: YearMapLayer | null,
  context: RiskTwinSpatialContext | null,
  _manualObservations: RiskTwinObservationInput[],
): EvidenceMapObject[] {
  const objects: EvidenceMapObject[] = [];
  const glacierGeometry = asGeometry(glacier?.geometry);
  if (glacier && glacierGeometry) {
    objects.push({
      id: `glacier:${glacier.rgi_id}`,
      kind: "glacier",
      name: glacier.name_ru || glacier.name || `RGI ${glacier.rgi_id}`,
      geometry: glacierGeometry,
      source: "RGI 7.0 inventory geometry",
      temporalCoverage: glacier.inventory_date || "inventory reference",
      maturity: "inventory_reference",
      visibleFact: "Инвентарная геометрия ледника доступна локально.",
      allowedClaim: "Можно показать границу инвентаря и справочную площадь.",
      prohibitedClaim: "Граница RGI не является текущим измерением опасности, объёма льда или прогнозом.",
      inspectorFacts: [
        { label: "RGI ID", value: glacier.rgi_id },
        { label: "Inventory area", value: `${glacier.rgi_area_km2.toFixed(3)} km²` },
        { label: "Inventory date", value: glacier.inventory_date || "not supplied" },
      ],
    });
  }

  if (yearLayer) {
    objects.push({
      id: `annual-segmentation:${yearLayer.year}:${yearLayer.method}`,
      kind: "annual_segmentation",
      name: `${yearLayer.year} segmentation screening`,
      geometry: annualGeometry(yearLayer),
      source: yearLayer.source,
      temporalCoverage: String(yearLayer.year),
      maturity: "local_artifact",
      visibleFact: "Локальный годовой screening-слой доступен для визуального сравнения.",
      allowedClaim: "Можно показать доступность артефакта и его явно указанную методику.",
      prohibitedClaim: yearLayer.caveat || "Screening-слой не является независимой валидацией или прогнозом.",
      inspectorFacts: [
        { label: "Method", value: yearLayer.method.toUpperCase() },
        { label: "Scope", value: yearLayer.scope },
        { label: "Caveat", value: yearLayer.caveat },
      ],
    });
  }

  if (!context) return objects;

  objects.push(
    ...featureObjects(
      [
        ...(context.layers.hma_gli_2015_2018.features as FeatureLike[]),
        ...(context.layers.tien_shan_lakes_2023.features as FeatureLike[]),
      ],
      "lake",
      "HMA GLI / Tien Shan lake inventory",
      "2015–2018 or 2023 inventory",
      (properties) => `Lake ID: ${sourceValue(properties.lake_id)}`,
      (properties) => [
        { label: "Lake ID", value: sourceValue(properties.lake_id) },
        { label: "Area", value: properties.area_m2 ? `${Number(properties.area_m2).toFixed(0)} m²` : "not supplied" },
        { label: "Inventory year", value: sourceValue(properties.inventory_year ?? properties.period) },
      ],
      "spatial_context",
      "Инвентарный водный объект находится в выбранном пространственном контексте.",
      "Можно показать геометрию, дату инвентаря и указанную площадь.",
      "Инвентарная близость не подтверждает связь с ледником, объём, состояние морены или вероятность события.",
    ),
    ...featureObjects(
      context.layers.hydrorivers.features as FeatureLike[],
      "river",
      "HydroRIVERS",
      "reference hydrography",
      (properties) => `HydroRIVERS reach ${sourceValue(properties.hyriv_id)}`,
      (properties) => [
        { label: "Reach ID", value: sourceValue(properties.hyriv_id) },
        { label: "Length", value: `${sourceValue(properties.length_km)} km` },
        { label: "Stream order", value: sourceValue(properties.stream_order) },
      ],
      "spatial_context",
      "Справочный гидрографический сегмент виден в локальном окне.",
      "Можно показать гидрографическую близость и атрибуты справочного сегмента.",
    ),
    ...featureObjects(
      context.layers.hydrobasins_level06.features as FeatureLike[],
      "basin",
      "HydroBASINS level 06",
      "reference basin geometry",
      (properties) => `HydroBASINS ${sourceValue(properties.hybas_id)}`,
      (properties) => [
        { label: "Basin ID", value: sourceValue(properties.hybas_id) },
        { label: "Upstream area", value: `${sourceValue(properties.upstream_area_km2)} km²` },
      ],
      "spatial_context",
      "Граница справочного бассейна видна в локальном окне.",
      "Можно показать бассейновый контекст исходного набора.",
    ),
    ...featureObjects(
      context.layers.historical_glof_events.features as FeatureLike[],
      "historical_record",
      "HMAGLOFDB historical record",
      "archive record date as supplied",
      (properties) => `Historical record ${sourceValue(properties.event_id)}`,
      (properties) => [
        { label: "Event ID", value: sourceValue(properties.event_id) },
        { label: "Year", value: sourceValue(properties.year) },
        { label: "Lake", value: sourceValue(properties.lake_name) },
      ],
      "archive_record",
      "Архивная запись находится в пространственном контексте.",
      "Можно показать идентификатор, дату и необходимость сверки с первичным источником.",
      "Архивная запись не является прогнозом, доказательством повторяемости или причинной связью с выбранным ледником.",
    ),
    ...featureObjects(
      context.impact_assets.available ? context.impact_assets.features.features as FeatureLike[] : [],
      "asset",
      context.impact_assets.source || "OSM planning context",
      "local planning extract",
      (properties) => sourceValue(properties.name) === "not supplied" ? `OSM ${sourceValue(properties.asset_type)}` : sourceValue(properties.name),
      (properties) => [
        { label: "Type", value: sourceValue(properties.asset_type) },
        { label: "Name", value: sourceValue(properties.name) },
      ],
      "planning_context",
      "Публичный объект доступен как планировочный пространственный контекст.",
      "Можно показать тип, имя и местоположение из локального extract.",
      "Объект на карте не подтверждает назначение, занятость, уязвимость или воздействие.",
    ),
  );

  return objects;
}

function rankedActionFor(variable: string, actions: RankedAction[]): string | undefined {
  return actions.find((action) => action.available !== false && action.target_variables?.includes(variable))?.label;
}

export function buildEvidenceIssues(
  _objects: EvidenceMapObject[],
  dataGaps: string[],
  rankedActions: RankedAction[],
): EvidenceIssue[] {
  return dataGaps.map((variable) => {
    const definition = GAP_DEFINITIONS[variable] ?? {
      decisionImpact: "low" as const,
      title: `Требуется проверка: ${variable}`,
      rationale: "Для этой переменной нет достаточного типизированного наблюдения.",
      nextAction: "Добавить проверяемое наблюдение с источником, временем и погрешностью.",
      blockedClaim: "Нельзя расширять вывод за пределы доступных доказательств.",
    };
    return {
      id: `gap-${variable}`,
      ...definition,
      nextAction: rankedActionFor(variable, rankedActions) ?? definition.nextAction,
    };
  }).sort((left, right) => ({ high: 0, medium: 1, low: 2 }[left.decisionImpact] - { high: 0, medium: 1, low: 2 }[right.decisionImpact]));
}
