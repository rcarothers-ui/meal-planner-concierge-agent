"""Configuration and Secure Secret Management package for the Meal Planning Concierge Agent."""

from meal_planner_agent.config.secrets_manager import (
    SecretManagerConfigClient,
    get_runtime_secret,
)

__all__ = ["SecretManagerConfigClient", "get_runtime_secret"]
