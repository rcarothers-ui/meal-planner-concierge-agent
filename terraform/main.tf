terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required Google Cloud APIs for Vertex AI Agent Engine, Observability & Security
resource "google_project_service" "required_apis" {
  for_each = toset([
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "firestore.googleapis.com",
    "dlp.googleapis.com",
    "cloudtrace.googleapis.com",
    "logging.googleapis.com",
    "discoveryengine.googleapis.com",
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# 2. Dedicated Least-Privilege Service Account for the Meal Planning Concierge Agent
resource "google_service_account" "meal_planner_agent_sa" {
  account_id   = "meal-planner-concierge-sa"
  display_name = "Automated Meal Planning Concierge Agent Service Account"
}

resource "google_project_iam_member" "agent_least_privilege_roles" {
  for_each = toset([
    "roles/aiplatform.user",
    "roles/secretmanager.secretAccessor",
    "roles/datastore.user",
    "roles/dlp.user",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.meal_planner_agent_sa.email}"
}

# 3. Google Cloud Secret Manager Secrets (Zero Hardcoded Keys in Code)
resource "google_secret_manager_secret" "usda_api_secret" {
  secret_id = "usda-fooddata-central-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "instacart_api_secret" {
  secret_id = "instacart-partner-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "gcal_oauth_secret" {
  secret_id = "google-calendar-oauth-credentials"
  replication {
    auto {}
  }
}

# 4. Persistent Session Database: Google Cloud Firestore
resource "google_firestore_database" "meal_planner_session_db" {
  project     = var.project_id
  name        = "meal-planner-sessions"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# 5. Vertex AI Vector Search Index for Long-Term Dietary & Recipe Embeddings
resource "google_vertex_ai_index" "dietary_memory_vector_index" {
  region       = var.region
  display_name = "meal-planner-dietary-memory-index"
  description  = "Vector index for household dietary preferences and nutritional recipes"
  index_update_method = "STREAM_UPDATE"

  metadata {
    contents_delta_uri = "gs://${google_storage_bucket.agent_engine_staging.name}/vector_index_init"
    config {
      dimensions                  = 768
      approximate_neighbors_count = 15
      distance_measure_type       = "COSINE_DISTANCE"
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 500
          leaf_nodes_to_search_percent = 7
        }
      }
    }
  }
}

# 6. Staging Bucket for `adk deploy agent_engine`
resource "google_storage_bucket" "agent_engine_staging" {
  name                        = "${var.project_id}-adk-staging"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
}

# 7. Cloud Run Deployment for ADK API & Web Server
resource "google_cloud_run_v2_service" "meal_planner_adk_service" {
  name     = "meal-planner-concierge-agent"
  location = var.region

  template {
    service_account = google_service_account.meal_planner_agent_sa.email
    containers {
      image = var.container_image
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }
      env {
        name = "SECRET_USDA_FOODDATA_CENTRAL_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.usda_api_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SECRET_INSTACART_PARTNER_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.instacart_api_secret.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}
