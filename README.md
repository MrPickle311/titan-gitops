# Titan GitOps

GitOps repository for the Titan homelab Kubernetes cluster. All infrastructure and workloads are managed declaratively via ArgoCD using an App-of-Apps pattern.

## Cluster Overview

| Property | Value |
|---|---|
| OS | Talos Linux |
| Orchestrator | Kubernetes |
| GitOps | ArgoCD (App-of-Apps) |
| Ingress | ingress-nginx |
| TLS | cert-manager with self-signed homelab CA |
| Storage | OpenEBS hostpath |
| Load Balancer | MetalLB (L2 mode) |
| Cluster Management UI | Rancher |

---

## Repository Structure

```
titan-gitops/
├── bootstrap/          # ArgoCD Application definitions — App-of-Apps root
├── infrastructure/     # Core cluster infrastructure (namespaces, cert-manager, registry, metallb, homepage)
├── databases/          # Database workloads (Postgres, Redis, Kafka, pgAdmin, RedisInsight, Kafka UI)
├── workloads/          # Business microservices (payment, wallet, ledger, export-batch, mock-regulatory)
├── metrics/            # Helm chart deploying the full observability stack
└── talos/              # Talos OS machine configs and patches — applied via talosctl, NOT ArgoCD
```

---

### bootstrap/

Contains one ArgoCD `Application` manifest per logical group. The `infra` Application points here, making this the App-of-Apps root. Any new top-level Application must be registered here.

---

### infrastructure/

Raw Kubernetes manifests for foundational cluster resources:

- **cluster-config/**: cert-manager `ClusterIssuer` and `Certificate` resources that establish the homelab internal CA (`homelab-ca-issuer`). All TLS in the cluster chains to this CA. Uses a self-signed bootstrap issuer to issue the root CA cert, which is then used by `homelab-ca-issuer` for all other certificates.
- **docker-storage/**: Self-hosted container registry (`registry.homelab`) backed by a 50Gi OpenEBS PVC. The registry UI is deployed alongside it for image browsing.
- **metallb-config/**: MetalLB `L2Advertisement` and `IPAddressPool` defining the load balancer IP range (`10.0.0.200–10.0.0.254`).
- **homepage/**: Cluster dashboard (gethomepage.dev) with read-only Kubernetes API access via ClusterRole/ClusterRoleBinding.
- `applications-namespace.yaml`: Declares the `applications` namespace with `privileged` pod security policy. Required by JVM-based services that use Java agents attached via `JAVA_TOOL_OPTIONS`.
- `kustomization.yaml`: Kustomize entry point for `cluster-config` ArgoCD Application. Only includes resources unique to cluster bootstrap — resources with their own ArgoCD Application are excluded to avoid `SharedResourceWarning`.

---

### databases/

Each file or subdirectory manages one database stack via a dedicated ArgoCD Application:

| Component | Type | Namespace | Notes |
|---|---|---|---|
| postgres | Bitnami Helm chart | databases | Credentials from `postgres-credentials` Secret |
| redis | Bitnami redis-cluster Helm chart | databases | 6 nodes, 1 replica. Credentials from `redis-cluster-credentials` Secret. Prometheus exporter enabled. Uses `bitnamilegacy` image repo due to Bitnami image policy change. |
| kafka | Bitnami Kafka Helm chart | messaging | Used by all services for event streaming |
| kafka-ui/ | Custom manifests | messaging | Provectus Kafka UI + Confluent Schema Registry + Kafka Exporter (Grafana dashboard 7589 compatible) |
| pgadmin/ | Custom manifests | databases | pgAdmin 4 for Postgres query and administration |
| redisinsight/ | Custom manifests | databases | RedisInsight 2.x for Redis cluster inspection. Auto-registers the cluster connection on pod startup via a Node.js postStart lifecycle hook. Encryption key from `redisinsight-credentials` Secret. |

---

### workloads/

Spring Boot microservices forming the Titan application domain. Each service manifest includes:

- `Deployment` — runs the service image from `registry.homelab`. Injects OpenTelemetry Java agent and Pyroscope profiler via an init container that downloads the agents to a shared in-memory volume.
- `Service` — exposes the HTTP port within the cluster.
- `ServiceMonitor` — instructs Prometheus Operator to scrape `/actuator/prometheus` every 15 seconds. Requires `release: kube-prometheus-stack` label to be discovered by the deployed Prometheus instance.
- `Ingress` — exposes the service externally via ingress-nginx with TLS terminated by the homelab CA.

| Service | Port | Host |
|---|---|---|
| payment-service | 8080 | payment.homelab |
| wallet-service | 8081 | wallet.homelab |
| ledger-service | 8082 | ledger.homelab |
| export-batch-service | 8083 | export-batch.homelab |
| mock-regulatory-service | 8084 | mock-regulatory.homelab |

All images are pulled from `registry.homelab/<service-name>:latest` with `imagePullPolicy: Always` to ensure fresh deployments.

The OpenTelemetry and Pyroscope agents are configured to:
- Export traces to Tempo via OTLP (`tempo.monitoring.svc.cluster.local:4318`)
- Send continuous profiles to Pyroscope (`pyroscope.monitoring.svc.cluster.local:4040`)
- Enrich log lines with `trace_id` and `span_id` for Loki correlation
- Enable Kafka observation for distributed trace propagation across service boundaries

---

### metrics/

A local Helm chart that deploys the full observability stack as ArgoCD Applications:

| Component | Purpose |
|---|---|
| kube-prometheus-stack | Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics |
| Loki | Log aggregation from all cluster workloads |
| Tempo | Distributed tracing — receives OTLP from all services |
| Pyroscope | Continuous profiling — receives JFR data from all services |
| metrics-server | Kubernetes resource metrics (CPU/memory for `kubectl top`) |

Grafana is exposed at `grafana.homelab`. Pre-configured data sources:
- Prometheus (metrics)
- Loki (logs, with trace ID extraction regex `trace_id=([0-9a-fA-F]+)`)
- Tempo (traces, linked to Loki and Pyroscope)
- Pyroscope (profiles, correlated by `service.name` tag)
- JSON API data sources for direct service data (payment, wallet, ledger, export-batch)

---

### talos/

Talos Linux machine configuration files. Applied directly via `talosctl` — not synced by ArgoCD.

| File | Purpose |
|---|---|
| `controlplane.yaml` | Full Talos machine config for the control plane node |
| `worker.yaml` | Full Talos machine config for worker nodes |
| `cp.yaml` | Minimal control plane bootstrap config used during initial cluster creation |
| `patch-node1.yaml` | Node-specific hostname and network patch for node1 |
| `patch-node2.yaml` | Node-specific hostname and network patch for node2 |
| `patch-worker1.yaml` | Node-specific hostname and network patch for worker1 |
| `patch-storage.yaml` | Talos patch enabling OpenEBS hostpath storage requirements |
| `patch-local-docker-registry.yaml` | Configures Talos container runtime to trust and use `registry.homelab` without TLS verification |
| `talosconfig` | `talosctl` client configuration — contains cluster endpoint and certificates |

> **Security**: `talosconfig`, `controlplane.yaml`, and `worker.yaml` contain TLS certificates and machine secrets. These must never be committed to a public repository. Use SOPS + age or Sealed Secrets for encryption before storing sensitive configs in git.

---

## Secrets Bootstrap

Secrets are not managed by ArgoCD. Create them manually before ArgoCD syncs the relevant Applications.

### LocalStack
```bash
kubectl create secret generic localstack-pro-token \
  --namespace localstack \
  --from-literal=token="<LOCALSTACK_PRO_TOKEN>"
```

### Databases namespace
```bash
kubectl create namespace databases
kubectl label namespace databases pod-security.kubernetes.io/enforce=privileged --overwrite
kubectl label namespace databases pod-security.kubernetes.io/warn=privileged --overwrite

kubectl create secret generic postgres-credentials \
  --namespace databases \
  --from-literal=postgres-password="<POSTGRES_PASSWORD>"

kubectl create secret generic redis-cluster-credentials \
  --namespace databases \
  --from-literal=redis-password="<REDIS_PASSWORD>"
```

### Applications namespace
```bash
kubectl create secret generic postgres-credentials \
  --namespace applications \
  --from-literal=postgres-password="<POSTGRES_PASSWORD>"
```

### Grafana
```bash
kubectl create secret generic grafana-credentials \
  --namespace monitoring \
  --from-literal=admin-user="admin" \
  --from-literal=admin-password="<GRAFANA_PASSWORD>"
```

### RedisInsight encryption key
```bash
kubectl create secret generic redisinsight-credentials \
  --namespace databases \
  --from-literal=encryption-key="<RANDOM_32_CHAR_KEY>"
```

---

## Observability Architecture

All services emit three correlated observability signals via trace IDs injected by the OpenTelemetry Java agent:

| Signal | Tool | Collection |
|---|---|---|
| Metrics | Prometheus | `ServiceMonitor` scrapes `/actuator/prometheus` every 15s |
| Logs | Loki | stdout logs enriched with `trace_id` and `span_id` in log pattern |
| Traces | Tempo | OTLP push from OTel Java agent |
| Profiles | Pyroscope | JFR continuous profiling via Pyroscope Java agent |

Grafana correlation links:
- Trace → Logs: extracts `trace_id` from Tempo span, queries Loki with `trace_id` filter
- Trace → Profiles: links Tempo span to Pyroscope profile by `service.name` tag

---

## Adding a New Microservice

1. Create `workloads/<service-name>.yaml` with `Deployment`, `Service`, `ServiceMonitor`, and `Ingress`.
2. The `workloads` ArgoCD Application auto-syncs — no bootstrap change needed.
3. Optionally add a Homepage entry in `infrastructure/homepage/config/services.yaml`.

## Adding a New Infrastructure Component

1. Create `infrastructure/<component>/` with manifests or a Helm Application yaml.
2. Create `bootstrap/<component>-app.yaml` as an ArgoCD `Application` pointing to that path.
3. Commit and push — the `infra` App-of-Apps auto-syncs and picks it up.
4. If the component has manifests included via `infrastructure/kustomization.yaml`, ensure they are NOT also managed by a separate ArgoCD Application to avoid `SharedResourceWarning`.

### pgAdmin
```bash
kubectl create secret generic pgadmin-credentials \
  --namespace databases \
  --from-literal=admin-email="<PGADMIN_ADMIN_EMAIL>" \
  --from-literal=admin-password="<PGADMIN_ADMIN_PASSWORD>"
```

### Rancher
```bash
kubectl create secret generic rancher-credentials \
  --namespace cattle-system \
  --from-literal=bootstrapPassword="<RANCHER_BOOTSTRAP_PASSWORD>"
```

---

## Manual Cluster Resources

The following resources **must be created manually** before ArgoCD can successfully sync the corresponding Applications. ArgoCD does not manage these — they are cluster-side prerequisites.

### Summary Table

| Secret Name | Namespace | Required By | Keys |
|---|---|---|---|
| `localstack-pro-token` | `localstack` | LocalStack | `token` |
| `postgres-credentials` | `databases` | Postgres Helm chart | `postgres-password` |
| `postgres-credentials` | `applications` | All microservices | `postgres-password` |
| `redis-cluster-credentials` | `databases` | Redis Helm chart + RedisInsight | `redis-password` |
| `redisinsight-credentials` | `databases` | RedisInsight | `encryption-key` |
| `pgadmin-credentials` | `databases` | pgAdmin | `admin-email`, `admin-password` |
| `grafana-credentials` | `monitoring` | kube-prometheus-stack | `admin-user`, `admin-password` |
| `rancher-credentials` | `cattle-system` | Rancher Helm chart | `bootstrapPassword` |

### Namespaces That Must Pre-Exist

Some namespaces require specific pod security labels that ArgoCD cannot set during creation. Create them manually:

```bash
kubectl create namespace databases
kubectl label namespace databases \
  pod-security.kubernetes.io/enforce=privileged \
  pod-security.kubernetes.io/warn=privileged \
  --overwrite

kubectl create namespace messaging
kubectl label namespace messaging \
  pod-security.kubernetes.io/enforce=privileged \
  pod-security.kubernetes.io/warn=privileged \
  --overwrite
```

> The `applications` namespace is created automatically by the `cluster-config` ArgoCD Application via `applications-namespace.yaml`. The `privileged` label is applied there declaratively.

### Create All Secrets — Full Script

Run this once on a fresh cluster before triggering ArgoCD sync:

```bash
# LocalStack
kubectl create namespace localstack
kubectl create secret generic localstack-pro-token \
  --namespace localstack \
  --from-literal=token="<LOCALSTACK_PRO_TOKEN>"

# Databases namespace
kubectl create namespace databases
kubectl label namespace databases pod-security.kubernetes.io/enforce=privileged --overwrite
kubectl label namespace databases pod-security.kubernetes.io/warn=privileged --overwrite

kubectl create secret generic postgres-credentials \
  --namespace databases \
  --from-literal=postgres-password="<POSTGRES_PASSWORD>"

kubectl create secret generic redis-cluster-credentials \
  --namespace databases \
  --from-literal=redis-password="<REDIS_PASSWORD>"

kubectl create secret generic redisinsight-credentials \
  --namespace databases \
  --from-literal=encryption-key="<RANDOM_32_CHAR_KEY>"

kubectl create secret generic pgadmin-credentials \
  --namespace databases \
  --from-literal=admin-email="<PGADMIN_ADMIN_EMAIL>" \
  --from-literal=admin-password="<PGADMIN_ADMIN_PASSWORD>"

# Applications namespace (microservices need access to shared Postgres)
kubectl create secret generic postgres-credentials \
  --namespace applications \
  --from-literal=postgres-password="<POSTGRES_PASSWORD>"

# Monitoring
kubectl create namespace monitoring
kubectl create secret generic grafana-credentials \
  --namespace monitoring \
  --from-literal=admin-user="admin" \
  --from-literal=admin-password="<GRAFANA_PASSWORD>"

# Rancher
kubectl create namespace cattle-system
kubectl create secret generic rancher-credentials \
  --namespace cattle-system \
  --from-literal=bootstrapPassword="<RANCHER_BOOTSTRAP_PASSWORD>"
```

### Verify All Secrets Exist

Use this to confirm all required secrets are present before ArgoCD sync:

```bash
kubectl get secret localstack-pro-token -n localstack
kubectl get secret postgres-credentials -n databases
kubectl get secret postgres-credentials -n applications
kubectl get secret redis-cluster-credentials -n databases
kubectl get secret redisinsight-credentials -n databases
kubectl get secret pgadmin-credentials -n databases
kubectl get secret grafana-credentials -n monitoring
kubectl get secret rancher-credentials -n cattle-system
```
