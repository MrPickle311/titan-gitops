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
| Storage | OpenEBS hostpath provisioner |
| Load Balancer | MetalLB (L2 mode, range `10.0.0.200–10.0.0.254`) |
| Cluster Management | Rancher |

---

## Repository Navigation

| Directory | Description | README |
|---|---|---|
| `bootstrap/` | ArgoCD Application definitions — App-of-Apps root | [bootstrap/README.md](bootstrap/README.md) |
| `infrastructure/` | Core cluster infrastructure (cert-manager, registry, metallb, homepage) | [infrastructure/README.md](infrastructure/README.md) |
| `databases/` | Database workloads (Postgres, Redis, Kafka, pgAdmin, RedisInsight, Kafka UI) | [databases/README.md](databases/README.md) |
| `workloads/` | Business microservices (payment, wallet, ledger, export-batch, mock-regulatory) | [workloads/README.md](workloads/README.md) |
| `metrics/` | Full observability stack (Prometheus, Loki, Tempo, Pyroscope) | [metrics/README.md](metrics/README.md) |
| `talos/` | Talos OS machine configs and patches — applied via `talosctl`, not ArgoCD | [talos/README.md](talos/README.md) |

---

## Prerequisites — Manual Cluster Resources

These resources must be created **before** ArgoCD syncs. ArgoCD does not manage them.

### Namespaces Requiring Pod Security Labels

```bash
kubectl create namespace databases
kubectl label namespace databases \
  pod-security.kubernetes.io/enforce=privileged \
  pod-security.kubernetes.io/warn=privileged --overwrite

kubectl create namespace messaging
kubectl label namespace messaging \
  pod-security.kubernetes.io/enforce=privileged \
  pod-security.kubernetes.io/warn=privileged --overwrite

kubectl create namespace chaos-mesh
kubectl label namespace chaos-mesh \
  pod-security.kubernetes.io/enforce=privileged \
  pod-security.kubernetes.io/warn=privileged --overwrite
```

> The `applications` namespace is created declaratively by `cluster-config` ArgoCD Application with the correct labels. No manual step needed.

### Required Secrets

| Secret | Namespace | Keys | Required By |
|---|---|---|---|
| `localstack-pro-token` | `localstack` | `token` | LocalStack |
| `postgres-credentials` | `databases` | `postgres-password` | Postgres chart |
| `postgres-credentials` | `applications` | `postgres-password` | All microservices |
| `redis-cluster-credentials` | `databases` | `redis-password` | Redis chart, RedisInsight |
| `redisinsight-credentials` | `databases` | `encryption-key` | RedisInsight |
| `pgadmin-credentials` | `databases` | `admin-email`, `admin-password` | pgAdmin |
| `grafana-credentials` | `monitoring` | `admin-user`, `admin-password` | kube-prometheus-stack |
| `rancher-credentials` | `cattle-system` | `bootstrapPassword` | Rancher chart |

### Full Bootstrap Script

```bash
# LocalStack
kubectl create namespace localstack
kubectl create secret generic localstack-pro-token \
  --namespace localstack \
  --from-literal=token="<LOCALSTACK_PRO_TOKEN>"

# Databases
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
  --from-literal=admin-email="<PGADMIN_EMAIL>" \
  --from-literal=admin-password="<PGADMIN_PASSWORD>"

# Applications (microservices share Postgres)
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

### Verify

```bash
for ns_secret in \
  "localstack/localstack-pro-token" \
  "databases/postgres-credentials" \
  "databases/redis-cluster-credentials" \
  "databases/redisinsight-credentials" \
  "databases/pgadmin-credentials" \
  "applications/postgres-credentials" \
  "monitoring/grafana-credentials" \
  "cattle-system/rancher-credentials"; do
  ns=$(echo $ns_secret | cut -d/ -f1)
  secret=$(echo $ns_secret | cut -d/ -f2)
  kubectl get secret $secret -n $ns -o name 2>/dev/null || echo "MISSING: $secret in $ns"
done
```

---

## Adding New Components

- **Microservice**: add `workloads/<name>.yaml` — see [workloads/README.md](workloads/README.md)
- **Infrastructure tool**: add `infrastructure/<name>/` + `bootstrap/<name>-app.yaml` — see [bootstrap/README.md](bootstrap/README.md)
- **Database**: add `databases/<name>-app.yaml` + register in `bootstrap/databases-app.yaml` — see [databases/README.md](databases/README.md)
