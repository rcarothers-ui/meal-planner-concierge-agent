variable "project_id" {
  description = "Google Cloud Project ID hosting the Meal Planning Concierge Agent."
  type        = string
  default     = "gcp-meal-planner-prod"
}

variable "region" {
  description = "Primary Google Cloud region for Vertex AI Agent Engine and Cloud Run."
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "Artifact Registry container image URI for the ADK agent service."
  type        = string
  default     = "us-central1-docker.pkg.dev/gcp-meal-planner-prod/agents/meal-planner-concierge:latest"
}
