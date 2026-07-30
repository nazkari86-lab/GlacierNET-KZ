import type { GlacierRecord, RiskTwinObservationInput, RiskTwinSpatialContext, YearMapLayer } from "@/lib/api";

export type EvidenceKind = "glacier" | "annual_segmentation" | "lake" | "river" | "corridor" | "basin" | "historical_record" | "asset";
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
  isRoute?: boolean;
  screening?: {
    rank: number;
    observationPriority: number;
    distanceToRgiBoundaryM: number;
    areaM2: number;
    areaChangePercent: number | null;
    previousMatchDistanceM: number | null;
    flags: string[];
  };
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

function contextFeatures(layer: unknown): FeatureLike[] {
  if (!layer || typeof layer !== "object") return [];
  const features = (layer as { features?: unknown }).features;
  return Array.isArray(features) ? features as FeatureLike[] : [];
}

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

function finiteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

function featureObjects(
  features: FeatureLike[],
  kind: Exclude<EvidenceKind, "glacier" | "annual_segmentation">,
  source: string,
  temporalCoverage: string,
  makeName: (properties: Record<string, unknown>) => string,
  makeFacts: (properties: Record<string, unknown>) => Array<{ label: string; value: string }>,
  maturity: EvidenceMaturity,
  visibleFact: string | ((properties: Record<string, unknown>) => string),
  allowedClaim: string,
  prohibitedClaim = PROXIMITY_LIMIT,
): EvidenceMapObject[] {
  return features.flatMap((feature, index) => {
    const geometry = asGeometry(feature.geometry);
    if (!geometry) return [];
    const properties = feature.properties ?? {};
    const sourceId = sourceValue(properties.lake_id ?? properties.hyriv_id ?? properties.hybas_id ?? properties.event_id ?? properties.osm_id ?? properties.id ?? index + 1);
    const observationPriority = finiteNumber(properties.observation_priority_0_100);
    const screeningRank = finiteNumber(properties.screening_rank);
    const distanceToRgiBoundaryM = finiteNumber(properties.distance_to_rgi_boundary_m);
    const areaM2 = finiteNumber(properties.area_current_m2 ?? properties.area_m2);
    const areaChangePercent = finiteNumber(properties.area_change_percent);
    const previousMatchDistanceM = finiteNumber(properties.geometric_match_distance_m);
    const flags = Array.isArray(properties.screening_flags) ? properties.screening_flags.map(String) : [];
    return [{
      id: `${kind}:${sourceId}`,
      kind,
      name: makeName(properties),
      geometry,
      source,
      temporalCoverage,
      maturity,
      visibleFact: typeof visibleFact === "function" ? visibleFact(properties) : visibleFact,
      allowedClaim,
      prohibitedClaim,
      inspectorFacts: makeFacts(properties),
      isRoute: properties.relation === "graph_derived_downstream_planning_route",
      ...(observationPriority !== null && screeningRank !== null && distanceToRgiBoundaryM !== null && areaM2 !== null ? {
        screening: {
          rank: screeningRank,
          observationPriority,
          distanceToRgiBoundaryM,
          areaM2,
          areaChangePercent,
          previousMatchDistanceM,
          flags,
        },
      } : {}),
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

  const candidatesByLakeId = new Map(
    (context.screening_candidates ?? [])
      .filter((candidate) => candidate.lake_id)
      .map((candidate, index) => [String(candidate.lake_id), { ...candidate, screening_rank: index + 1 }]),
  );
  const currentLakes = contextFeatures(context.layers?.tien_shan_lakes).map((feature) => {
    const properties = feature.properties ?? {};
    const candidate = candidatesByLakeId.get(String(properties.lake_id ?? ""));
    return candidate ? {
      ...feature,
      properties: {
        ...properties,
        ...candidate,
        screening_flags: candidate.flags,
      },
    } : feature;
  });

  objects.push(
    ...featureObjects(
      currentLakes,
      "lake",
      `Tien Shan lake inventory ${context.query.lake_inventory_year}`,
      `${context.query.lake_inventory_year} inventory; ${context.query.previous_lake_inventory_year ?? "no previous"} comparison where geometric match is explicit`,
      (properties) => {
        const priority = finiteNumber(properties.observation_priority_0_100);
        return priority === null
          ? `Lake ID: ${sourceValue(properties.lake_id)}`
          : `Озеро ${sourceValue(properties.lake_id)} · проверка ${priority.toFixed(0)}/100`;
      },
      (properties) => [
        { label: "Lake ID", value: sourceValue(properties.lake_id) },
        { label: "Площадь инвентаря", value: finiteNumber(properties.area_current_m2 ?? properties.area_m2) === null ? "not supplied" : `${Number(properties.area_current_m2 ?? properties.area_m2).toFixed(0)} м²` },
        { label: "Inventory year", value: sourceValue(properties.inventory_year ?? properties.period) },
        ...(finiteNumber(properties.area_change_percent) === null ? [] : [{ label: `Изменение к ${sourceValue(properties.previous_inventory_year)}`, value: `${Number(properties.area_change_percent).toFixed(1)}%` }]),
        ...(finiteNumber(properties.distance_to_rgi_boundary_m) === null ? [] : [{ label: "До границы RGI", value: `${Number(properties.distance_to_rgi_boundary_m).toFixed(0)} м` }]),
        ...(finiteNumber(properties.geometric_match_distance_m) === null ? [] : [{ label: "Расстояние геометрического match", value: `${Number(properties.geometric_match_distance_m).toFixed(0)} м` }]),
      ],
      "spatial_context",
      (properties) => {
        const priority = finiteNumber(properties.observation_priority_0_100);
        const distance = finiteNumber(properties.distance_to_rgi_boundary_m);
        return priority === null || distance === null
          ? "Инвентарный водный объект находится в выбранном пространственном контексте."
          : `Кандидат №${Number(properties.screening_rank)}: ${distance.toFixed(0)} м до границы RGI; приоритет проверки ${priority.toFixed(0)}/100.`;
      },
      "Можно показать геометрию, дату инвентаря и указанную площадь.",
      "Инвентарная близость не подтверждает связь с ледником, объём, состояние морены или вероятность события.",
    ),
    ...featureObjects(
      contextFeatures(context.downstream_route?.features),
      "river",
      "HydroRIVERS NEXT_DOWN route",
      "graph-derived downstream planning route",
      (properties) => `Route segment ${sourceValue(properties.route_sequence)} · ${sourceValue(properties.hyriv_id)}`,
      (properties) => [
        { label: "Route sequence", value: sourceValue(properties.route_sequence) },
        { label: "Reach ID", value: sourceValue(properties.hyriv_id) },
        { label: "Next downstream", value: sourceValue(properties.next_downstream_id) },
        { label: "Length", value: `${sourceValue(properties.length_km)} km` },
      ],
      "spatial_context",
      "Сегмент получен последовательным обходом реальной связи NEXT_DOWN.",
      "Можно показать топологический маршрут HydroRIVERS и порядок сегментов.",
      "Это не гидродинамический путь, не время добегания, не зона затопления и не официальное предупреждение.",
    ),
    ...featureObjects(
      contextFeatures(context.layers?.hydrorivers),
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
      contextFeatures(context.layers?.hydrobasins_level06),
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
      contextFeatures(context.layers?.historical_glof_events),
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
      contextFeatures(context.downstream_route?.planning_assets),
      "asset",
      "OSM objects inside HydroRIVERS planning corridor",
      "local planning extract",
      (properties) => sourceValue(properties.name) === "not supplied" ? `OSM ${sourceValue(properties.asset_type)}` : sourceValue(properties.name),
      (properties) => [
        { label: "Type", value: sourceValue(properties.asset_type) },
        { label: "Name", value: sourceValue(properties.name) },
        { label: "Relation", value: "inside planning corridor" },
      ],
      "planning_context",
      "Публичный объект пересекает планировочный коридор вокруг топологического маршрута.",
      "Можно назначить объект на проверку назначения и актуальности.",
      "Пересечение коридора не означает воздействие, затопление, ущерб или необходимость эвакуации.",
    ),
    ...featureObjects(
      context.impact_assets?.available ? contextFeatures(context.impact_assets.features) : [],
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

  const corridorGeometry = asGeometry(context.downstream_route?.corridor?.geometry);
  if (context.downstream_route?.available && corridorGeometry) {
    objects.push({
      id: "corridor:hydrorivers-downstream",
      kind: "corridor",
      name: `HydroRIVERS planning corridor · ${context.downstream_route.corridor_width_m ?? 750} m`,
      geometry: corridorGeometry,
      source: "Derived buffer around HydroRIVERS NEXT_DOWN route",
      temporalCoverage: "reference hydrography",
      maturity: "planning_context",
      visibleFact: `${context.downstream_route.route_length_km ?? "—"} km graph route · ${context.downstream_route.planning_asset_count ?? 0} public objects to verify.`,
      allowedClaim: "Можно показать область поиска объектов для дальнейшей проверки.",
      prohibitedClaim: context.downstream_route.interpretation ?? "Коридор не является зоной затопления или воздействия.",
      inspectorFacts: [
        { label: "Route status", value: context.downstream_route.status },
        { label: "Route length", value: `${context.downstream_route.route_length_km ?? "—"} km` },
        { label: "Corridor width", value: `${context.downstream_route.corridor_width_m ?? "—"} m` },
        { label: "Objects to verify", value: String(context.downstream_route.planning_asset_count ?? 0) },
      ],
    });
  }

  return objects;
}

function rankedActionFor(variable: string, actions: RankedAction[]): string | undefined {
  return actions.find((action) => action.available !== false && action.target_variables?.includes(variable))?.label;
}

export function buildEvidenceIssues(
  objects: EvidenceMapObject[],
  dataGaps: string[],
  rankedActions: RankedAction[],
): EvidenceIssue[] {
  const firstId = (kinds: EvidenceKind[]) => kinds.map((kind) => objects.find((item) => item.kind === kind)?.id).find(Boolean);
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
      objectId: variable === "exposed_asset_count" ? firstId(["asset", "glacier"]) : variable === "channel_capacity_m3_s" ? firstId(["river", "glacier"]) : firstId(["lake", "glacier"]),
      ...definition,
      nextAction: rankedActionFor(variable, rankedActions) ?? definition.nextAction,
    };
  }).sort((left, right) => ({ high: 0, medium: 1, low: 2 }[left.decisionImpact] - { high: 0, medium: 1, low: 2 }[right.decisionImpact]));
}
