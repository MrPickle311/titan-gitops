
Requirements:

```bash
kubectl create secret generic localstack-pro-token \
  --namespace localstack \
  --from-literal=token="LOCALSTACK_PRO_TOKEN"
```

For databases: 
```bash
kubectl create namespace databases
kubectl label namespace databases pod-security.kubernetes.io/enforce=privileged --overwrite
kubectl label namespace databases pod-security.kubernetes.io/warn=privileged --overwrite
```

