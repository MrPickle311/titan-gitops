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
