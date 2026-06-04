import json
import os

BATCH_DASH_DIR = '/home/damian/sandbox/homelab/titan-gitops/metrics/dashboards/batch'
KAFKA_RELATED_MESSAGES_FILE = os.path.join(BATCH_DASH_DIR, 'kafka-related-messages.json')
EXECUTION_DETAILS_FILE = os.path.join(BATCH_DASH_DIR, 'execution-details.json')
KAFKA_PG_DATA_FILE = os.path.join(BATCH_DASH_DIR, 'kafka-pg-data.json')
JOB_INSTANCES_FILE = os.path.join(BATCH_DASH_DIR, 'job-instances.json')
JOB_OVERVIEW_FILE = os.path.join(BATCH_DASH_DIR, 'job-overview.json')

# Helper to load/save JSON
def load_json(path):
    with open(path, 'r') as f: return json.load(f)
def save_json(data, path):
    with open(path, 'w') as f: json.dump(data, f, indent=2)

kafka_dash = load_json(KAFKA_RELATED_MESSAGES_FILE)
exec_dash = load_json(EXECUTION_DETAILS_FILE)
pg_dash = load_json(KAFKA_PG_DATA_FILE)
inst_dash = load_json(JOB_INSTANCES_FILE)

# 1. execution-details.json link -> kafka-pg-data.json
for panel in exec_dash['panels']:
    if panel['title'] == "Kafka - Step Related Data":
        panel['fieldConfig']['defaults']['links'] = [
            {
              "title": "View Payments in DB",
              "url": "/d/afnr5i5gpysxsb/kafka-postgres-payments-data?var-stepExecutionId=${__data.fields[\"Step ID\"]}"
            }
        ]
save_json(exec_dash, EXECUTION_DETAILS_FILE)

# 2. kafka-pg-data.json variables and links -> kafka-related-messages.json
pg_dash['templating']['list'] = [
    {
      "current": {"selected": False, "text": "", "value": ""},
      "hide": 0, "name": "stepExecutionId", "options": [{"selected": True, "text": "", "value": ""}],
      "query": "", "skipUrlSync": False, "type": "textbox"
    },
    {
      "current": {"selected": False, "text": "All", "value": "$__all"},
      "datasource": {"type": "grafana-postgresql-datasource", "uid": "ffnpozixx84xsb"},
      "definition": "SELECT json_array_elements_text(COALESCE(SERIALIZED_CONTEXT, SHORT_CONTEXT)::json->'processedPaymentIds') FROM BATCH_STEP_EXECUTION_CONTEXT WHERE STEP_EXECUTION_ID = $stepExecutionId",
      "hide": 2, "includeAll": True, "multi": True, "name": "paymentIds",
      "options": [],
      "query": "SELECT json_array_elements_text(COALESCE(SERIALIZED_CONTEXT, SHORT_CONTEXT)::json->'processedPaymentIds') FROM BATCH_STEP_EXECUTION_CONTEXT WHERE STEP_EXECUTION_ID = $stepExecutionId",
      "refresh": 1, "regex": "", "skipUrlSync": False, "sort": 0, "type": "query"
    }
]
for panel in pg_dash['panels']:
    if panel['title'] == "Postgres Payments Data":
        panel['fieldConfig']['defaults']['links'] = [
            {
              "title": "View Kafka Messages",
              "url": "/d/afnq60u73wr28c/kafka-aggregation?var-stepExecutionId=${stepExecutionId}"
            }
        ]
save_json(pg_dash, KAFKA_PG_DATA_FILE)

# 3. job-instances.json link -> execution-details.json
for panel in inst_dash['panels']:
    if panel['title'] == "Job Instances Table":
        panel['fieldConfig']['defaults']['links'] = [
            {
              "title": "View Executions ->",
              "url": "/d/ffnpwkpnqb474c/execution-details?var-jobInstanceId=${__data.fields[\"Job Instance ID\"]}"
            }
        ]
save_json(inst_dash, JOB_INSTANCES_FILE)

# 4. kafka-related-messages.json
# Ensure it still has the correct templating and transformations
kafka_dash['templating']['list'] = pg_dash['templating']['list']
save_json(kafka_dash, KAFKA_RELATED_MESSAGES_FILE)

print("Dashboards updated successfully.")
