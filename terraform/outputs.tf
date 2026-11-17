output "cloud_run_service_uri" {
  description = "HTTPS endpoint URL of the deployed ADK Meal Planning Concierge Agent."
  value       = google_cloud_run_v2_service.meal_planner_adk_service.uri
}

output "agent_service_account_email" {
  description = "Least-privilege IAM Service Account email used by the agent."
  value       = google_service_account.meal_planner_agent_sa.email
}

output "adk_staging_bucket_name" {
  description = "GCS staging bucket used by `adk deploy agent_engine`."
  value       = google_storage_bucket.agent_engine_staging.name
}

output "firestore_database_name" {
  description = "Firestore database storing persistent multi-turn household sessions."
  value       = google_firestore_database.meal_planner_session_db.name
}
