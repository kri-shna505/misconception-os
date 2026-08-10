import type {
  MisconceptionEvolutionState,
} from "../types";


type EvolutionBadgeProps = {
  state:
    | MisconceptionEvolutionState
    | null
    | undefined;

  compact?: boolean;
  showDescription?: boolean;
};


type EvolutionPresentation = {
  label: string;
  description: string;
  className: string;
};


const EVOLUTION_PRESENTATIONS: Record<
  MisconceptionEvolutionState,
  EvolutionPresentation
> = {
  newly_detected: {
    label: "Newly detected",
    description:
      "This misconception was detected for the first time in the current learning sequence.",
    className:
      "evolution-badge evolution-badge-new",
  },

  repeated: {
    label: "Repeated",
    description:
      "The same misconception appeared again without a clear reduction in severity.",
    className:
      "evolution-badge evolution-badge-repeated",
  },

  improving: {
    label: "Improving",
    description:
      "The misconception remains, but the diagnosis state or confidence indicates progress.",
    className:
      "evolution-badge evolution-badge-improving",
  },

  corrected: {
    label: "Corrected",
    description:
      "A previously detected misconception is no longer present in the latest retry.",
    className:
      "evolution-badge evolution-badge-corrected",
  },

  replaced: {
    label: "Replaced",
    description:
      "The previous misconception changed into a different misconception.",
    className:
      "evolution-badge evolution-badge-replaced",
  },

  uncertain: {
    label: "Uncertain",
    description:
      "The available evidence is not strong enough to classify the learning transition reliably.",
    className:
      "evolution-badge evolution-badge-uncertain",
  },
};


function getEvolutionPresentation(
  state:
    | MisconceptionEvolutionState
    | null
    | undefined
): EvolutionPresentation {
  if (!state) {
    return {
      label: "Not evaluated",
      description:
        "No misconception evolution record is available for this attempt yet.",
      className:
        "evolution-badge evolution-badge-empty",
    };
  }

  return EVOLUTION_PRESENTATIONS[state];
}


export default function EvolutionBadge({
  state,
  compact = false,
  showDescription = false,
}: EvolutionBadgeProps) {
  const presentation =
    getEvolutionPresentation(state);

  if (compact) {
    return (
      <span
        className={presentation.className}
        title={presentation.description}
        aria-label={`Learning progress: ${presentation.label}`}
      >
        {presentation.label}
      </span>
    );
  }

  return (
    <div
      className="evolution-status"
      aria-label={`Learning progress: ${presentation.label}`}
    >
      <span
        className={presentation.className}
      >
        {presentation.label}
      </span>

      {showDescription && (
        <p className="evolution-description">
          {presentation.description}
        </p>
      )}
    </div>
  );
}


export function getEvolutionLabel(
  state:
    | MisconceptionEvolutionState
    | null
    | undefined
): string {
  return getEvolutionPresentation(
    state
  ).label;
}


export function getEvolutionDescription(
  state:
    | MisconceptionEvolutionState
    | null
    | undefined
): string {
  return getEvolutionPresentation(
    state
  ).description;
}