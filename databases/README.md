# databases/

Database workloads deployed via dedicated ArgoCD Applications. Each component is independently synced and versioned.

## Components

| Component | Chart / Type | Namespace | Version |
|---|---|---|---|
| Postgres | Bitnami `postgresql` Helm | `databases` | see `postgres-app.yaml` |
| Redis | Bitnami `redis-cluster` Helm | `databases` | see `redis-app.yaml` |
| Kafka | Bitnami `kafka` Helm | `messaging` | see `kafka.yaml` |
| Kafka UI | Custom manifests | `messaging` | `kafka-ui/manifests.yaml` |
| pgAdmin | Custom manifests | `databases` | `pgadmin/manifests.yaml` |
| RedisInsight | Custom manifests | `databases` | `redisinsight/manifests.yaml` |

## Required Secrets

Create these before ArgoCD syncs this directory:

```bash
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
  --from-literal=admin-email="<EMAIL>" \
  --from-literal=admin-password="<PASSWORD>"
```

## Notes

**Redis** uses the `bitnamilegacy` image repository for both the cluster and its Prometheus exporter. Bitnami moved older images to this repo after their image policy change — direct `bitnami/` references for these versions will fail to pull.

**Kafka UI** (`kafka-ui/manifests.yaml`) deploys three components:
1. Confluent Schema Registry — manages Avro/Protobuf schemas
2. Provectus Kafka UI — web UI for topic/consumer inspection
3. Kafka Exporter — exposes broker and consumer group metrics compatible with Grafana dashboard ID 7589

**RedisInsight** auto-registers the Redis cluster connection on pod startup via a Node.js `postStart` lifecycle hook. It polls the local API until ready, then registers `redis-redis-cluster.databases.svc.cluster.local:6379`. The encryption key is read from the `redisinsight-credentials` Secret.

**pgAdmin** reads the Postgres password from the `postgres-credentials` Secret (same secret as used by the Postgres chart). Admin credentials are in `pgadmin-credentials`.
