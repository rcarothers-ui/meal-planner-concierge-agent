.PHONY: install test eval run-cli run-web deploy-agent-engine terraform-plan

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

eval:
	python3 -m evals.evaluate_agent
	adk eval meal_planner_agent evals/golden_dataset.json || true

run-cli:
	adk run meal_planner_agent

run-web:
	adk web meal_planner_agent --port 8000

deploy-agent-engine:
	adk deploy agent_engine \
		--project=$${GOOGLE_CLOUD_PROJECT} \
		--region=$${GOOGLE_CLOUD_LOCATION:-us-central1} \
		--staging_bucket=gs://$${GOOGLE_CLOUD_PROJECT}-adk-staging \
		--display_name="Automated-Meal-Planning-Concierge-Agent" \
		meal_planner_agent

terraform-plan:
	cd terraform && terraform init -backend=false && terraform validate && terraform plan
