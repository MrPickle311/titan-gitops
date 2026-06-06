# workloads/

Spring Boot microservices forming the Titan application domain. Each service is defined in a single YAML file containing all Kubernetes resources for that service.

## Services

| Service | Port | Host | Description |
|---|---|---|---|
| `payment-service` | 8080 | `payment.homelab` | Handles payment processing, publishes events to Kafka |
| `wallet-service` | 8081 | `wallet.homelab` | Manages wallet balances, consumes payment events |
| `ledger-service` | 8082 | `ledger.homelab` | Accounting ledger, consumes events from payment and wallet |
| `export-batch-service` | 8083 | `export-batch.homelab` | Batch export of ledger data |
| `mock-regulatory-service` | 8084 | `mock-regulatory.homelab` | Simulates regulatory reporting endpoint |

All images are pulled from `registry.homelab/<service-name>:latest` with `imagePullPolicy: Always`.

## Manifest Structure

Each `<service>.yaml` contains:

| Resource | Purpose |
|---|---|
| `Deployment` | Runs the service. Injects OTel + Pyroscope agents via init container |
| `Service` | Exposes the HTTP port within the cluster |
| `ServiceMonitor` | Instructs Prometheus to scrape `/actuator/prometheus` every 15s |
| `Ingress` | Exposes the service at `<name>.homelab` with TLS via homelab CA |

## Observability Agents

All services use an **init container** to download agent JARs to a shared in-memory volume (`emptyDir`) before the main container starts:

- `opentelemetry-javaagent.jar` — instruments the JVM for traces and metrics
- `pyroscope-otel.jar` — Pyroscope extension for OpenTelemetry (correlates profiles with traces)
- `pyroscope.jar` — Pyroscope Java agent for continuous JFR profiling

The agents are activated via `JAVA_TOOL_OPTIONS` in the main container. Signal destinations:

| Signal | Destination |
|---|---|
| Traces | `tempo.monitoring.svc.cluster.local:4318` (OTLP/HTTP) |
| Profiles | `pyroscope.monitoring.svc.cluster.local:4040` |
| Metrics | Scraped by Prometheus via `ServiceMonitor` |
| Logs | stdout, enriched with `trace_id` and `span_id` in the log pattern, collected by Loki |

Kafka observation is enabled on all services (`SPRING_KAFKA_LISTENER_OBSERVATION_ENABLED=true`) so trace context propagates across service boundaries through Kafka message headers.

## Required Secrets

```bash
kubectl create secret generic postgres-credentials \
  --namespace applications \
  --from-literal=postgres-password="<POSTGRES_PASSWORD>"
```

## Adding a New Service

1. Create `workloads/<service-name>.yaml` following the pattern of existing services.
2. The `workloads` ArgoCD Application (`bootstrap/applications-app.yaml`) auto-syncs the new file — no bootstrap change required.
3. Optionally register the service in `infrastructure/homepage/config/services.yaml` for the cluster dashboard.
