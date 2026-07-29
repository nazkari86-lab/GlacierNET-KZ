import type { GlacierRecord, RiskTwinSpatialContext } from "@/lib/api";
import type { EvidenceMapObject } from "@/lib/riskTwinEvidence";

type Candidate = RiskTwinSpatialContext["screening_candidates"][number];

export type ActionAudience = "satellite" | "field" | "decision" | "research";

export interface ActionPlanStep {
  id: string;
  title: string;
  instruction: string;
  acceptance: string;
  blockedClaim: string;
}

/** The first action is deliberately separate from the complete workflow.
 * A selected case should answer "what do I do now?" before showing every
 * possible measurement or research task. */
export interface CaseFocus {
  headline: string;
  reasons: string[];
  nextStep: ActionPlanStep;
}

export type DecisionGateStatus = "observed" | "verify" | "blocked";

/** A compact, claim-safe answer to "what can this case support today?" */
export interface DecisionGate {
  status: DecisionGateStatus;
  label: string;
  detail: string;
}

export interface CaseActionPlan {
  caseId: string;
  coordinates: string;
  facts: Array<{ label: string; value: string }>;
  summary: string;
  focus: CaseFocus;
  decisionGates: DecisionGate[];
  actions: Record<ActionAudience, ActionPlanStep[]>;
  guardrails: string[];
}

export interface SelectedObjectAdvice {
  title: string;
  rationale: string;
  facts: Array<{ label: string; value: string }>;
  nextStep: ActionPlanStep;
  guardrails: string[];
}

const formatArea = (areaM2: number) => `${(areaM2 / 1_000_000).toFixed(3)} км² (${Math.round(areaM2).toLocaleString("ru-RU")} м²)`;

export function buildCaseActionPlan(glacier: GlacierRecord, candidate: Candidate, year: number): CaseActionPlan {
  const inventoryYear = candidate.inventory_year;
  const previousYear = candidate.previous_inventory_year;
  const hasReliableMatch = candidate.area_change_percent !== null && candidate.geometric_match_distance_m !== null && candidate.geometric_match_distance_m <= 300;
  const change = hasReliableMatch
    ? `${candidate.area_change_percent! > 0 ? "+" : ""}${candidate.area_change_percent!.toFixed(1)}%`
    : "не установлено: нет match ≤300 м";
  const contextStep = candidate.distance_to_rgi_boundary_m <= 1000
    ? {
        id: "glacier-lake-context",
        title: "Проверить ледниково-озёрный контекст",
        instruction: `Проверить по снимку и рельефу участок между контуром RGI и озером: расстояние сейчас ${candidate.distance_to_rgi_boundary_m.toFixed(0)} м. Зафиксировать, есть ли видимый водосборный или моренный барьер.`,
        acceptance: "Добавить снимок, дату, границу анализа и короткое заключение с указанием метода.",
        blockedClaim: "Близость к RGI сама по себе не доказывает связь озера с ледником.",
      }
    : {
        id: "do-not-link-by-distance",
        title: "Не приписывать озеро леднику по расстоянию",
        instruction: `Озеро находится в ${candidate.distance_to_rgi_boundary_m.toFixed(0)} м от границы RGI. Оставить его как пространственный контекст до отдельной проверки водосбора.`,
        acceptance: "Есть независимое обоснование связи: рельеф, сток или проверенный источник.",
        blockedClaim: "Нельзя называть озеро ледниково-связанным только по близости на карте.",
      };

  const imageStep = hasReliableMatch
    ? {
        id: "validate-area-change",
        title: "Подтвердить изменение площади по исходным сценам",
        instruction: `Проверить контуры ${previousYear} и ${inventoryYear} на исходных снимках в одинаковой сезонной фазе. Текущий геометрический match: ${candidate.geometric_match_distance_m!.toFixed(0)} м; скрининг-изменение: ${change}.`,
        acceptance: "Контуры и сцены сохранены с датой, источником, облачностью и оценкой погрешности площади.",
        blockedClaim: "Скрининг-изменение площади не является измерением объёма воды или вероятности события.",
      }
    : {
        id: "create-verified-outline-pair",
        title: "Создать подтверждённую пару контуров",
        instruction: previousYear === null
          ? `Для ${inventoryYear} это базовый инвентарь без более ранней локальной пары. Найти совместимый более ранний контур и вручную задокументировать, почему сравнение допустимо.`
          : `Найти исходные сцены для ${previousYear} и ${inventoryYear}, вручную сверить границы воды и сформировать пару с геометрическим match не дальше 300 м. Текущий ближайший контур: ${candidate.geometric_match_distance_m?.toFixed(0) ?? "—"} м.`,
        acceptance: "Есть два проверенных контура, источник каждой сцены и match ≤300 м либо явное решение, что сравнение недопустимо.",
        blockedClaim: "До этого нельзя заявлять рост или сокращение площади озера.",
      };

  const fieldStep: ActionPlanStep = {
    id: "field-profile",
    title: "Снять профиль воды, преграды и выпуска",
    instruction: "На месте измерить уровень воды, свободный борт, состояние естественной преграды, геометрию выпуска и минимум пять поперечных сечений русла. Для каждой точки сохранить координаты, время, метод и погрешность.",
    acceptance: "В Evidence Ledger внесены численные значения, единицы, неопределённость и проверяемый источник для каждого измерения.",
    blockedClaim: "Без этих измерений нельзя говорить о переполнении, устойчивости преграды, маршруте потока или последствиях.",
  };

  const decisionStep: ActionPlanStep = {
    id: "decision-brief",
    title: "Сформировать ограниченное решение о проверке",
    instruction: "Передать координаты, источник инвентаря, приоритет проверки и конкретный следующий шаг группе наблюдения. Указать, что это задача сбора доказательств, а не предупреждение.",
    acceptance: "В карточке решения указаны ответственный, срок, метод проверки и ссылка на экспорт кейса.",
    blockedClaim: "Нельзя выпускать GLOF-предупреждение, оценку пострадавших или эвакуационный план без валидации и модели распространения.",
  };

  const researchStep: ActionPlanStep = {
    id: "reproducibility-package",
    title: "Экспортировать воспроизводимый пакет кейса",
    instruction: `Сохранить RGI ID ${glacier.rgi_id}, lake ID ${candidate.lake_id ?? "без ID"}, инвентарные годы ${previousYear ?? "нет"}→${inventoryYear}, порог match 300 м, исходные контуры и версию годового слоя ${year}.`,
    acceptance: "Экспорт содержит только наблюдаемые факты, источники и ограничения утверждений.",
    blockedClaim: "Нельзя выдавать локальный скрининг за внешнюю валидацию или экспертный gold label.",
  };

  const reasons = [
    hasReliableMatch
      ? `Для этого контура есть геометрическое сопоставление с ${previousYear} годом (${candidate.geometric_match_distance_m!.toFixed(0)} м); скрининг-изменение ${change} ещё нужно подтвердить по исходным сценам.`
      : previousYear === null
        ? `${inventoryYear} — базовый инвентарь без более ранней локальной пары, поэтому изменение площади не вычисляется.`
        : `Для этого контура нет допустимого сопоставления с ${previousYear} годом: ближайший контур ${candidate.geometric_match_distance_m?.toFixed(0) ?? "не указан"} м, а порог проверки — не более 300 м.`,
    candidate.distance_to_rgi_boundary_m <= 1000
      ? `Озеро находится в ${candidate.distance_to_rgi_boundary_m.toFixed(0)} м от границы RGI, поэтому после проверки контура нужно отдельно изучить водосбор и естественную преграду.`
      : `Озеро находится в ${candidate.distance_to_rgi_boundary_m.toFixed(0)} м от границы RGI; близость на карте сама по себе не подтверждает связь с ледником.`,
    `Приоритет наблюдения ${candidate.observation_priority_0_100.toFixed(0)}/100 задаёт порядок проверки, а не вероятность опасности.`,
    ...(candidate.flags.includes("historical_events_in_same_10km_context")
      ? ["В том же 10-км пространственном контексте есть архивные записи событий; это повод проверить первоисточники, а не прогноз для данного озера."]
      : []),
  ];

  const caseId = `${glacier.rgi_id}:${candidate.lake_id ?? `${candidate.latitude},${candidate.longitude}`}:${inventoryYear}`;
  return {
    caseId,
    coordinates: `${candidate.latitude.toFixed(6)}, ${candidate.longitude.toFixed(6)}`,
    facts: [
      { label: `Площадь ${inventoryYear}`, value: formatArea(candidate.area_current_m2) },
      { label: previousYear === null ? "Сравнение" : `К ${previousYear}`, value: change },
      { label: "До границы RGI", value: `${candidate.distance_to_rgi_boundary_m.toFixed(0)} м` },
      { label: "Приоритет проверки", value: `${candidate.observation_priority_0_100.toFixed(0)}/100` },
    ],
    summary: `Кейс ${caseId}. Озеро ${candidate.lake_id ?? "без ID"}: ${formatArea(candidate.area_current_m2)} в ${inventoryYear}; расстояние до границы RGI ${candidate.distance_to_rgi_boundary_m.toFixed(0)} м; изменение к ${previousYear ?? "предыдущему инвентарю"} ${change}. Следующий шаг: ${imageStep.title}.`,
    focus: {
      headline: imageStep.title,
      reasons,
      nextStep: imageStep,
    },
    decisionGates: [
      {
        status: "observed",
        label: `Инвентарный контур ${inventoryYear}`,
        detail: `Доступна площадь ${formatArea(candidate.area_current_m2)} и координаты объекта из локального инвентаря.`,
      },
      {
        status: hasReliableMatch ? "verify" : "blocked",
        label: previousYear === null ? "Изменение площади" : `Изменение площади ${previousYear}–${inventoryYear}`,
        detail: hasReliableMatch
          ? `Есть геометрический match ${candidate.geometric_match_distance_m!.toFixed(0)} м и скрининг ${change}; его нужно проверить по исходным сценам.`
          : previousYear === null
            ? `Это базовый инвентарь ${inventoryYear}: локальная более ранняя пара не выбрана, поэтому изменение площади не устанавливается.`
            : `Нет допустимого match ≤300 м, поэтому изменение площади пока не устанавливается.`,
      },
      {
        status: "blocked",
        label: "Связь озера с ледником",
        detail: `Расстояние ${candidate.distance_to_rgi_boundary_m.toFixed(0)} м — только пространственный контекст; нужны рельеф, сток или независимый источник.`,
      },
      {
        status: "blocked",
        label: "Уровень воды и состояние преграды",
        detail: "Требуются полевые измерения уровня, свободного борта, выпуска и естественной преграды.",
      },
      {
        status: "blocked",
        label: "Последствия для людей и инфраструктуры",
        detail: "Требуются проверенная экспозиция, модель распространения потока и операционная валидация.",
      },
    ],
    actions: {
      satellite: [imageStep, contextStep],
      field: [fieldStep],
      decision: [decisionStep],
      research: [researchStep],
    },
    guardrails: [
      "Приоритет проверки — не вероятность опасности и не официальный уровень тревоги.",
      "Инвентарная площадь не является объёмом воды, глубиной или состоянием морены.",
      "Без модели стока и распространения нельзя оценивать затронутых людей, здания или маршрут затопления.",
    ],
  };
}

/**
 * Give every selectable map object a useful next action.  Only candidates that
 * passed through the local screening receive the richer CaseActionPlan above;
 * this fallback stays intentionally modest so a raw inventory object is never
 * presented as a hazard case.
 */
export function buildSelectedObjectAdvice(object: EvidenceMapObject, year: number): SelectedObjectAdvice {
  const isLake = object.kind === "lake";
  const isAnnualLayer = object.kind === "annual_segmentation";
  const title = isLake
    ? object.screening
      ? "Открыть подтверждённый план этого озера"
      : "Проверить инвентарный контур выбранного озера"
    : isAnnualLayer
      ? `Проверить локальный слой сегментации ${year}`
      : `Использовать «${object.name}» только по назначению источника`;
  const instruction = isLake
    ? "Открыть исходную сцену, сверить водную границу с датой инвентаря и зафиксировать контур с источником и погрешностью. Только после этого сопоставлять его с другим годом или изучать рельеф вокруг него."
    : isAnnualLayer
      ? "Сравнить слой с исходной сценой и RGI-границей в том же окне. Сохранить дату, метод и ограничение артефакта; не интерпретировать растровый слой как готовую оценку опасности."
      : "Зафиксировать, какую пространственную роль объект играет в кейсе, и получить отдельные измерения для любого вывода о состоянии озера, преграды, русла или последствиях.";

  return {
    title,
    rationale: object.screening
      ? "Этот объект имеет скрининговые атрибуты. Если полный план не открылся, дождитесь загрузки локального контекста или выберите его в таблице кандидатов."
      : "Выбранный объект есть в локальном источнике, но ещё не является отобранным кандидатом с подтверждённым сравнением площадей.",
    facts: object.inspectorFacts.slice(0, 4),
    nextStep: {
      id: `inspect-${object.kind}`,
      title,
      instruction,
      acceptance: "Сохранены источник, дата, геометрия или измерение, метод проверки и явная погрешность.",
      blockedClaim: "До отдельной проверки нельзя делать выводы о связи с ледником, состоянии преграды, маршруте потока или опасности.",
    },
    guardrails: [
      "Выбор объекта на карте не является оценкой вероятности события или официальным предупреждением.",
    ],
  };
}
