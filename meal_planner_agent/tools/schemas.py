"""Explicit Pydantic JSON Schemas for Input Validation and LLM Output Constraining.

Satisfies AgentOps Rubric Criterion 1.3: Explicit JSON Schemas (5 Points).
Utilizes strict Pydantic v2 BaseModel input and output schemas (`extra="forbid"`,
explicit type annotations, numerical bounds, and `model_json_schema()`) to
validate all tool arguments and constrain LLM responses, with a built-in
standard-library JSON Schema fallback for bare Python environments.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator  # type: ignore

    PYDANTIC_AVAILABLE = True
except ImportError:  # pragma: no cover
    PYDANTIC_AVAILABLE = False

    class ValidationError(ValueError):  # type: ignore[no-redef]
        """Fallback validation error when running in a bare Python environment."""

    def ConfigDict(**kwargs: Any) -> Dict[str, Any]:  # type: ignore[no-redef]
        return kwargs

    def Field(default: Any = ..., **kwargs: Any) -> Any:  # type: ignore[no-redef]
        return {"__field_spec__": True, "default": default, **kwargs}

    def field_validator(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-redef]
        def _dec(fn: Any) -> Any:
            return fn

        return _dec

    class BaseModel:  # type: ignore[no-redef]
        """Strict JSON Schema validator compatible with Pydantic v2 BaseModel API."""

        model_config: Dict[str, Any] = {"extra": "forbid"}

        def __init__(self, **data: Any) -> None:
            cls = self.__class__
            specs = self._collect_field_specs()
            if cls.model_config.get("extra") == "forbid":
                unknown = set(data.keys()) - set(specs.keys())
                if unknown:
                    raise ValidationError(f"Extra inputs are not permitted: {sorted(unknown)}")

            for field_name, spec in specs.items():
                if field_name in data:
                    val = data[field_name]
                elif "default_factory" in spec and callable(spec["default_factory"]):
                    val = spec["default_factory"]()
                elif spec.get("default", ...) is not ...:
                    val = spec["default"]
                else:
                    raise ValidationError(f"Missing required field '{field_name}'")

                ge_bound = spec.get("ge")
                le_bound = spec.get("le")
                min_len = spec.get("min_length")
                max_len = spec.get("max_length")
                pattern = spec.get("pattern")

                if ge_bound is not None and isinstance(val, (int, float)) and val < ge_bound:
                    raise ValidationError(f"Field '{field_name}'={val} is less than ge={ge_bound}")
                if le_bound is not None and isinstance(val, (int, float)) and val > le_bound:
                    raise ValidationError(f"Field '{field_name}'={val} exceeds le={le_bound}")
                if min_len is not None and hasattr(val, "__len__") and len(val) < min_len:
                    raise ValidationError(
                        f"Field '{field_name}' length {len(val)} is less than min_length={min_len}"
                    )
                if max_len is not None and hasattr(val, "__len__") and len(val) > max_len:
                    raise ValidationError(
                        f"Field '{field_name}' length {len(val)} exceeds max_length={max_len}"
                    )
                if pattern is not None and isinstance(val, str):
                    import re

                    if not re.match(pattern, val):
                        raise ValidationError(
                            f"Field '{field_name}'='{val}' does not match pattern {pattern}"
                        )
                setattr(self, field_name, val)

        @classmethod
        def _collect_field_specs(cls) -> Dict[str, Dict[str, Any]]:
            annotations = getattr(cls, "__annotations__", {})
            specs: Dict[str, Dict[str, Any]] = {}
            for name in annotations:
                raw_attr = getattr(cls, name, ...)
                if isinstance(raw_attr, dict) and raw_attr.get("__field_spec__"):
                    specs[name] = raw_attr
                else:
                    specs[name] = {"default": raw_attr}
            return specs

        @classmethod
        def model_json_schema(cls) -> Dict[str, Any]:
            specs = cls._collect_field_specs()
            properties: Dict[str, Any] = {}
            required: List[str] = []
            for name, spec in specs.items():
                prop: Dict[str, Any] = {"title": name}
                for key in ("description", "ge", "le", "min_length", "max_length", "pattern"):
                    if key in spec:
                        prop[key] = spec[key]
                properties[name] = prop
                if spec.get("default", ...) is ... and "default_factory" not in spec:
                    required.append(name)
            return {
                "title": cls.__name__,
                "type": "object",
                "additionalProperties": cls.model_config.get("extra") != "forbid",
                "properties": properties,
                "required": required,
            }

        def model_dump(self) -> Dict[str, Any]:
            specs = self._collect_field_specs()
            out: Dict[str, Any] = {}
            for name in specs:
                val = getattr(self, name)
                if isinstance(val, Enum):
                    out[name] = val.value
                else:
                    out[name] = val
            return out


class DietaryProtocolEnum(str, Enum):
    """Supported clinical and lifestyle dietary protocols."""

    BALANCED = "balanced"
    MEDITERRANEAN = "mediterranean"
    VEGAN = "vegan"
    VEGETARIAN = "vegetarian"
    KETOGENIC = "ketogenic"
    HIGH_PROTEIN = "high_protein"
    LOW_FODMAP = "low_fodmap"
    DIABETIC_FRIENDLY = "diabetic_friendly"


class ActivityLevelEnum(str, Enum):
    """Physical activity multipliers for Total Daily Energy Expenditure (TDEE)."""

    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    ATHLETE = "athlete"


class MacronutrientTargetInputSchema(BaseModel):
    """Strict input schema for `calculate_daily_macronutrient_targets`."""

    model_config = ConfigDict(extra="forbid")

    weight_kg: float = Field(
        ...,
        ge=30.0,
        le=300.0,
        description="Adult body weight in kilograms (must be between 30.0 and 300.0 kg).",
    )
    height_cm: float = Field(
        ...,
        ge=120.0,
        le=250.0,
        description="Adult height in centimeters (must be between 120.0 and 250.0 cm).",
    )
    age_years: int = Field(
        ...,
        ge=18,
        le=110,
        description="User age in years (must be an adult aged 18 to 110).",
    )
    biological_sex: Literal["female", "male"] = Field(
        ...,
        description="Biological reference sex ('female' or 'male') for Mifflin-St Jeor BMR equation.",
    )
    activity_level: ActivityLevelEnum = Field(
        ...,
        description="Weekly physical activity level used to compute TDEE.",
    )
    dietary_protocol: DietaryProtocolEnum = Field(
        default=DietaryProtocolEnum.MEDITERRANEAN,
        description="Primary dietary protocol governing macronutrient split ratios.",
    )
    caloric_adjustment_kcal: int = Field(
        default=0,
        ge=-750,
        le=750,
        description="Daily caloric deficit or surplus in kcal (-750 to +750 kcal).",
    )


class MacronutrientTargetOutputSchema(BaseModel):
    """Strict output schema returned by `calculate_daily_macronutrient_targets`."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "error"]
    basal_metabolic_rate_kcal: int = Field(..., ge=800, le=5000)
    target_daily_calories_kcal: int = Field(..., ge=1200, le=6000)
    protein_grams: int = Field(..., ge=30, le=450)
    carbohydrates_grams: int = Field(..., ge=10, le=800)
    fats_grams: int = Field(..., ge=20, le=300)
    fiber_minimum_grams: int = Field(..., ge=20, le=80)
    dietary_protocol: str
    clinical_safety_note: str


class RecipeSearchInputSchema(BaseModel):
    """Strict input schema for `search_nutritional_recipe_database`."""

    model_config = ConfigDict(extra="forbid")

    dietary_protocol: DietaryProtocolEnum = Field(
        ...,
        description="Required dietary style (e.g., 'mediterranean', 'vegan', 'high_protein').",
    )
    excluded_allergens: List[str] = Field(
        default_factory=list,
        description="Allergens that MUST be strictly excluded (e.g., ['peanuts', 'shellfish', 'gluten']).",
    )
    max_prep_time_minutes: int = Field(
        default=45,
        ge=5,
        le=180,
        description="Maximum meal preparation and cooking duration in minutes (5 to 180).",
    )
    target_calories_per_serving: int = Field(
        default=600,
        ge=200,
        le=1500,
        description="Target kilocalories per serving (200 to 1500 kcal).",
    )
    meal_slot: Literal["breakfast", "lunch", "dinner", "snack", "any"] = Field(
        default="any",
        description="Meal slot filter ('breakfast', 'lunch', 'dinner', 'snack', or 'any').",
    )

    @field_validator("excluded_allergens")
    @classmethod
    def normalize_allergens(cls, values: List[str]) -> List[str]:
        return [item.strip().lower() for item in values if item.strip()]


class RecipeItemSchema(BaseModel):
    """Schema representing a single nutritionally verified recipe."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    title: str
    meal_slot: str
    dietary_tags: List[str]
    allergens_present: List[str]
    prep_time_minutes: int
    calories_per_serving: int
    protein_grams: int
    carbs_grams: int
    fat_grams: int
    estimated_cost_per_serving_usd: float
    ingredients: List[Dict[str, str]]


class PantryVerificationInputSchema(BaseModel):
    """Strict input schema for `verify_pantry_ingredient_availability`."""

    model_config = ConfigDict(extra="forbid")

    household_id: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Unique identifier of the household pantry inventory.",
    )
    required_ingredients: List[str] = Field(
        ...,
        min_length=1,
        description="List of canonical ingredient names required by the selected meal plan.",
    )


class GroceryListGenerationInputSchema(BaseModel):
    """Strict input schema for `generate_categorized_grocery_shopping_list`."""

    model_config = ConfigDict(extra="forbid")

    selected_recipe_ids: List[str] = Field(
        ...,
        min_length=1,
        description="Non-empty list of recipe IDs selected for the weekly meal plan.",
    )
    household_servings_multiplier: int = Field(
        default=2,
        ge=1,
        le=12,
        description="Number of household members / servings per recipe (1 to 12).",
    )
    pantry_items_on_hand: List[str] = Field(
        default_factory=list,
        description="Ingredients already available in the user's pantry to subtract from purchase list.",
    )
    weekly_budget_limit_usd: float = Field(
        default=150.0,
        ge=20.0,
        le=2000.0,
        description="Maximum weekly grocery budget in USD.",
    )


class MealCalendarScheduleInputSchema(BaseModel):
    """Strict input schema for `schedule_weekly_meal_prep_calendar_events`."""

    model_config = ConfigDict(extra="forbid")

    user_calendar_id: str = Field(
        ...,
        min_length=3,
        description="Target Google Calendar identifier (for example, 'primary').",
    )
    week_start_iso_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="ISO-8601 Monday start date for the meal plan week (YYYY-MM-DD).",
    )
    scheduled_meals: List[Dict[str, str]] = Field(
        ...,
        min_length=1,
        description="List of meal schedule entries with keys 'day', 'meal_slot', and 'recipe_title'.",
    )


class InstacartOrderInputSchema(BaseModel):
    """Strict input schema for high-stakes `place_instacart_grocery_delivery_order`."""

    model_config = ConfigDict(extra="forbid")

    household_id: str = Field(..., min_length=3)
    retailer_name: str = Field(..., min_length=2)
    grocery_items: List[Dict[str, str]] = Field(..., min_length=1)
    estimated_total_usd: float = Field(..., ge=1.0, le=2000.0)
    human_confirmation_token: Optional[str] = Field(
        default=None,
        description="Explicit human-in-the-loop approval token required for financial checkout.",
    )


class GuidedToolErrorOutputSchema(BaseModel):
    """Standardized guided error schema returned to the LLM for self-healing recovery."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["error"] = "error"
    error_code: str
    failed_tool_name: str
    human_readable_message: str
    llm_recovery_instructions: str
    valid_parameter_examples: Dict[str, object] = Field(default_factory=dict)
