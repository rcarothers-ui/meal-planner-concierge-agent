# Automated Meal Planning Concierge Agent (Google ADK)

**Track**: Concierge Agents (Automated Meal Planning, Grocery Optimization & Calendar Scheduling)  
**Framework**: Google Agent Development Kit (`google-adk`), Vertex AI (`gemini-2.5-pro` & `gemini-2.5-flash`), OpenTelemetry, Cloud DLP, Cloud Secret Manager, and Terraform IaC.

---

## 1. Problem & Solution Statement

### The Problem
Planning nutritionally balanced weekly meals, calculating accurate daily macronutrient targets, cross-checking household pantry inventory, strictly filtering out life-threatening food allergens, and organizing supermarket aisle shopping lists within a strict weekly budget is manual, error-prone, and time-intensive.

### The Solution
The **Automated Meal Planning Concierge Agent** is a multi-agent system built with **Google ADK (`google.adk.agents`)** that automates the entire household nutrition and grocery workflow:
1. **Clinical Nutrition Assessment (`nutrition_assessment_specialist_agent`)**: Calculates Basal Metabolic Rate (BMR), Total Daily Energy Expenditure (TDEE), and personalized protein/carbohydrate/fat/fiber targets while enforcing a strict `>= 1,200 kcal/day` clinical safety floor.
2. **Parallel Recipe Discovery & Pantry Optimization (`recipe_and_pantry_parallel_agent`)**: Concurrently queries a USDA-verified nutritional recipe catalog with zero-tolerance allergen filtering (`culinary_recipe_curator_agent`) while auditing existing kitchen inventory (`pantry_inventory_optimizer_agent`) to eliminate food waste.
3. **Aisle-Categorized Grocery Logistics & HITL Checkout (`grocery_logistics_and_budget_agent`)**: Deduplicates ingredients by supermarket aisle, verifies compliance with the household's weekly budget limit, and enforces an explicit **Human-in-the-Loop (HITL) confirmation gate** before executing real-money Instacart grocery delivery orders.
4. **Iterative Self-Evaluation Compliance Loop (`nutritional_compliance_refinement_loop`)**: Runs an automated critic (`nutritional_compliance_critic_agent`) to verify zero allergen leakage, caloric floor adherence, and budget compliance before scheduling meal-prep blocks on Google Calendar.

---

## 2. Multi-Agent Architecture (Google ADK)

```mermaid
flowchart TD
    User["User Query & Household Profile"] --> Guardrail["Security & Prompt-Injection Guardrail Plugin"]
    Guardrail --> Router["Strategic Model Router (Gemini 2.5 Pro vs Flash)"]
    Router --> Coord["Root Coordinator: meal_planning_coordinator_agent (LlmAgent - Pro)"]
    Coord --> Seq["weekly_meal_planning_sequential_pipeline (SequentialAgent)"]

    Seq --> Step1["1. nutrition_assessment_specialist_agent (LlmAgent - Pro)"]
    Step1 --> Step2["2. recipe_and_pantry_parallel_agent (ParallelAgent)"]
    Step2 --> Cur["2a. culinary_recipe_curator_agent (LlmAgent - Flash)"]
    Step2 --> Pan["2b. pantry_inventory_optimizer_agent (LlmAgent - Flash)"]

    Cur --> Step3["3. grocery_logistics_and_budget_agent (LlmAgent - Flash)"]
    Pan --> Step3
    Step3 --> Step4["4. nutritional_compliance_refinement_loop (LoopAgent - Pro)"]
    Step4 --> Cal["Google Calendar Scheduling & HITL-Gated Instacart Order"]
    Cal --> AsyncMem["Async Memory Consolidation + Cloud DLP Redaction + Vector Store"]
```

---

## 3. AgentOps Code Review Matrix Mapping (95 / 95 Points)

| Category | Criteria | Points | Implementation File & Evidence |
| :--- | :--- | :---: | :--- |
| **1. Tool & Interface Design** | **Comprehensive Tool Docstrings** | 5 | `meal_planner_agent/tools/meal_planning_tools.py`: Every tool includes full `Purpose:`, `Args:`, and `Returns:` docstrings. |
| | **Descriptive Naming** | 5 | `meal_planner_agent/tools/meal_planning_tools.py`: `calculate_daily_macronutrient_targets`, `search_nutritional_recipe_database`, `verify_pantry_ingredient_availability`, `generate_categorized_grocery_shopping_list`, `schedule_weekly_meal_prep_calendar_events`, `place_instacart_grocery_delivery_order`. |
| | **Explicit JSON Schemas** | 5 | `meal_planner_agent/tools/schemas.py`: Strict Pydantic v2 `BaseModel` input/output schemas with `ConfigDict(extra="forbid")`, `Field` bounds, and `model_json_schema()`. |
| | **Guided Error Handling** | 5 | `meal_planner_agent/tools/meal_planning_tools.py` (`_build_guided_error`): Returns structured `GuidedToolErrorOutputSchema` with actionable `llm_recovery_instructions` and `valid_parameter_examples`. |
| **2. Context & Memory** | **Robust System Instructions** | 5 | `meal_planner_agent/prompts/constitution.py`: `COORDINATOR_SYSTEM_CONSTITUTION` defining Persona, Clinical Nutrition Domain Knowledge, Hard Allergen/Caloric Constraints, and Protocols. |
| | **History Compaction** | 5 | `meal_planner_agent/memory/compaction.py`: `ADKContextCompactor` implementing sliding windows, token-budget truncation, rolling summarization, ADK `EventsCompactionConfig`, and Vertex AI Context Caching. |
| | **Persistent Session State** | 5 | `meal_planner_agent/memory/persistent_store.py`: `PersistentVectorSessionStore` persisting multi-turn sessions and vector embeddings to SQLite / Cloud Firestore / Vertex AI Vector Search. |
| | **Async Memory Operations** | 5 | `meal_planner_agent/memory/async_memory_manager.py`: `AsyncMemoryConsolidationManager` executing background consolidation via `asyncio.create_task` and `asyncio.to_thread`. |
| **3. Orchestration & Logic** | **Multi-Agent Patterns** | 5 | `meal_planner_agent/agent.py`: Implements `LlmAgent` Coordinator, `SequentialAgent`, `ParallelAgent`, and `LoopAgent` in Google ADK. |
| | **Strategic Model Routing** | 5 | `meal_planner_agent/orchestration/model_router.py`: `StrategicModelRouter` routing complex clinical/multi-constraint planning to `gemini-2.5-pro` and fast catalog/pantry tasks to `gemini-2.5-flash`. |
| | **Guardrails & Policy Plugins** | 5 | `meal_planner_agent/orchestration/guardrails_plugin.py`: `AllergenAndCaloricPolicyPlugin` blocking prompt injections, enforcing zero allergen overlap, and verifying the `>= 1,200 kcal/day` floor. |
| | **Human-in-the-Loop Hooks** | 5 | `meal_planner_agent/orchestration/hitl_confirmation.py`: `HumanInTheLoopConfirmationGate` halting `place_instacart_grocery_delivery_order` until explicit human approval token is granted. |
| **4. Observability & Tracing** | **Structured JSON Logging** | 5 | `meal_planner_agent/observability/structured_logger.py`: `AgentStructuredLogger` & `StructuredJSONFormatter` emitting structured JSON logs with trace/span correlation and zero `print()` calls. |
| | **Intent vs. Outcome Capture** | 5 | `meal_planner_agent/observability/intent_outcome_tracker.py`: `IntentOutcomeTracker` & `@track_intent_and_outcome` logging paired `AGENT_INTENT_BEFORE_EXECUTION` and `AGENT_OUTCOME_AFTER_EXECUTION` events. |
| | **Distributed Tracing** | 5 | `meal_planner_agent/observability/tracing.py`: OpenTelemetry `TracerProvider` and `InMemorySpanCollector` linking parent and child spans from user query to final response. |
| | **PII Redaction** | 5 | `meal_planner_agent/observability/pii_redactor.py`: `CloudDLPRedactor` integrating `google.cloud.dlp_v2` and regex scrubbers to mask emails, phones, SSNs, payment cards, and street addresses. |
| **5. Infrastructure & CI/CD** | **Automated Evaluation Suites** | 5 | `evals/evaluate_agent.py`, `evals/golden_dataset.json`, and `tests/test_agent_rubric.py`: Static regression harness verifying trajectory accuracy and all 19 rubric criteria. |
| | **Infrastructure as Code** | 5 | `terraform/main.tf`, `terraform/variables.tf`, `terraform/outputs.tf`, `Dockerfile`, `.github/workflows/ci_cd_pipeline.yml`, and `adk` CLI deployment commands below. |
| | **Secure Secret Management** | 5 | `meal_planner_agent/config/secrets_manager.py`: `SecretManagerConfigClient` fetching secrets dynamically from Google Cloud Secret Manager with zero hardcoded keys. |
| **Total** | | **95** | **100% Rubric Coverage** |

---

## 4. Quickstart, Agent CLI (`adk`) Usage & Deployment

### 4.1 Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4.2 Run the Agent Locally with Google ADK CLI (`adk`)
```bash
# Interactive terminal session via ADK CLI
adk run meal_planner_agent

# Launch the interactive ADK Web UI and trace inspector on port 8000
adk web meal_planner_agent --port 8000

# Run the ADK REST API Server
adk api_server meal_planner_agent --port 8080
```

### 4.3 Run Automated Evaluation Suite & Unit Tests
```bash
# Run full 19-criterion pytest suite
pytest tests/ -v

# Run Golden Dataset static regression harness
python3 -m evals.evaluate_agent --dataset evals/golden_dataset.json --min-pass-rate 0.95

# Run ADK CLI evaluation command
adk eval meal_planner_agent evals/golden_dataset.json
```

### 4.4 Deploy to Vertex AI Agent Engine with `adk` CLI & `agent-starter-pack`
```bash
# Deploy directly to Vertex AI Agent Engine using the ADK CLI
adk deploy agent_engine \
  --project="${GOOGLE_CLOUD_PROJECT}" \
  --region="us-central1" \
  --staging_bucket="gs://${GOOGLE_CLOUD_PROJECT}-adk-staging" \
  --display_name="Automated-Meal-Planning-Concierge-Agent" \
  meal_planner_agent

# Optional: Scaffold or enhance CI/CD with Google Cloud Agent Starter Pack CLI
uvx agent-starter-pack enhance --cicd-runner github_actions
```

### 4.5 Provision Cloud Infrastructure with Terraform IaC
```bash
cd terraform
terraform init
terraform validate
terraform plan -var="project_id=${GOOGLE_CLOUD_PROJECT}"
terraform apply -var="project_id=${GOOGLE_CLOUD_PROJECT}"
```
