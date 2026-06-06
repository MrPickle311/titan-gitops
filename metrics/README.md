# metrics/

A local Helm chart that deploys the full observability stack as ArgoCD Applications. The chart lives in this directory (`Chart.yaml` + `templates/`) and is deployed by the `metrics` ArgoCD Application.

## Stack Components

| Component | Purpose | URL |
|---|---|---|
| kube-prometheus-stack | Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics | `grafana.homelab` |
| Loki | Log aggregation from all cluster pods | internal only |
| Tempo | Distributed tracing — OTLP receiver | internal only |
| Pyroscope | Continuous profiling — JFR receiver | internal only |
| metrics-server | Kubernetes resource metrics (`kubectl top`) | internal only |

## Observability Signal Flow

```
Microservice JVM
  ├── OTel Java Agent  ──── OTLP traces ────► Tempo
  ├── Pyroscope Agent  ──── JFR profiles ───► Pyroscope
  ├── Actuator /metrics ─── scraped ──────── ► Prometheus
  └── stdout logs ─────── collected by ────► Loki
                                                  ▲
                                             Promtail

Grafana
  ├── Data source: Prometheus
  ├── Data source: Loki       (trace_id regex links logs ↔ traces)
  ├── Data source: Tempo      (links traces → logs and traces → profiles)
  ├── Data source: Pyroscope  (linked from Tempo by service.name tag)
  └── Data sources: JSON API  (payment, wallet, ledger, export-batch services)
```

## Grafana Pre-configured Correlations

- **Trace → Logs**: Tempo span opens Loki query filtered by `trace_id` extracted via regex `trace_id=([0-9a-fA-F]+)`
- **Trace → Profiles**: Tempo span links to Pyroscope profile matched by `service.name` tag
- **Logs → Traces**: Loki derived field extracts `trace_id` from log lines and links to Tempo

## Required Secrets

```bash
kubectl create secret generic grafana-credentials \
  --namespace monitoring \
  --from-literal=admin-user="admin" \
  --from-literal=admin-password="<GRAFANA_PASSWORD>"
```

---

## Grafana Data Sources

All data sources are provisioned automatically via the `kube-prometheus-stack` Helm chart values. No manual setup required.

| UID | Name | Type | Endpoint | Notes |
|---|---|---|---|---|
| *(auto)* | Prometheus | `prometheus` | in-cluster | Default metrics source |
| `loki` | Loki | `loki` | `http://loki.monitoring.svc.cluster.local:3100` | Derived field extracts `trace_id` → links to Tempo |
| `tempo` | Tempo | `tempo` | `http://tempo.monitoring.svc.cluster.local:3100` | Links traces → Loki, traces → Pyroscope |
| `pyroscope` | Pyroscope | `pyroscope` | `http://pyroscope.monitoring.svc.cluster.local:4040` | Linked from Tempo by `service.name` tag |
| `kafka-datasource` | Kafka | `hamedkarbasi93-kafka-datasource` | `kafka.messaging.svc.cluster.local:9092` | Used by Kafka dashboards |
| `infinity` | Infinity | `yesoreyeram-infinity-datasource` | n/a | Generic HTTP/JSON data source |
| `json-api-payment` | JSON API - Payment | `marcusolsson-json-datasource` | `http://payment-service.applications.svc.cluster.local:8080` | Direct service data |
| `json-api-wallet` | JSON API - Wallet | `marcusolsson-json-datasource` | `http://wallet-service.applications.svc.cluster.local:8081` | Direct service data |
| `json-api-ledger` | JSON API - Ledger | `marcusolsson-json-datasource` | `http://ledger-service.applications.svc.cluster.local:8082` | Direct service data |
| `json-api-export-batch` | JSON API - Export Batch | `marcusolsson-json-datasource` | `http://export-batch-service.applications.svc.cluster.local:8083` | Direct service data |

### Installed Grafana Plugins

The following plugins are installed automatically at Grafana startup:

| Plugin ID | Purpose |
|---|---|
| `marcusolsson-json-datasource` | JSON API data source for direct REST queries to services |
| `hamedkarbasi93-kafka-datasource` | Native Kafka data source for topic/consumer group dashboards |
| `yesoreyeram-infinity-datasource` | Universal HTTP/CSV/JSON/GraphQL data source |

---

## Dashboards

Dashboards are stored as JSON files under `dashboards/` and loaded into Grafana automatically via the Grafana sidecar. Each JSON file is packaged into a `ConfigMap` by `templates/dashboards-cm.yaml` using a Helm range loop. The `k8s-sidecar-target-directory` annotation controls the Grafana folder.

### applications/

| File | Dashboard Name | Data Sources Used |
|---|---|---|
| `actuator-ui.json` | Spring Boot Actuator UI | Prometheus |
| `continuous-profiling.json` | Continuous Profiling | Pyroscope, Tempo |
| `distributed-traces.json` | Distributed Traces | Tempo, Loki |
| `jvm.json` | JVM Metrics | Prometheus |
| `payment-browser.json` | Payment Browser | JSON API - Payment |
| `payments-statemachine.json` | Payment State Machine | JSON API - Payment |
| `spring-boot-stats.json` | Spring Boot Statistics | Prometheus |

### batch/

| File | Dashboard Name | Data Sources Used |
|---|---|---|
| `execution-details.json` | Batch Execution Details | Prometheus, JSON API - Export Batch |
| `job-instances.json` | Batch Job Instances | Prometheus |
| `job-overview.json` | Batch Job Overview | Prometheus |
| `kafka-pg-data.json` | Kafka → Postgres Data Flow | Kafka, Prometheus |
| `kafka-related-messages.json` | Kafka Related Messages | Kafka |

### cluster/

| File | Dashboard Name | Data Sources Used |
|---|---|---|
| `sample-dashboard.json` | Cluster Overview | Prometheus |

### databases/

| File | Dashboard Name | Data Sources Used |
|---|---|---|
| `kafka-data.json` | Kafka Data | Kafka, Prometheus |
| `kafka-exporter-overview.json` | Kafka Exporter Overview (ID 7589) | Prometheus |
| `postgres.json` | PostgreSQL Overview | Prometheus |
| `redis.json` | Redis Cluster Overview | Prometheus |

### Adding a Dashboard

1. Export the dashboard JSON from Grafana (`Share → Export → Save to file`).
2. Place the file in the appropriate `dashboards/<folder>/` subdirectory.
3. The Helm chart automatically packages it into a ConfigMap on next sync.
4. The Grafana sidecar detects the new ConfigMap and loads the dashboard without a Grafana restart.
