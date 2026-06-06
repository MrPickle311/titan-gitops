# bootstrap/

Contains ArgoCD `Application` manifests implementing the **App-of-Apps** pattern. The root `infra` Application points to this directory, causing ArgoCD to discover and manage all other Applications automatically.

## How It Works

```
ArgoCD
 └── infra Application (watches bootstrap/)
      ├── certmanager.yaml        → deploys cert-manager
      ├── ingress-nginx-app.yaml  → deploys ingress-nginx
      ├── openebs-app.yaml        → deploys OpenEBS
      ├── metallb-app.yaml        → deploys MetalLB
      ├── metallb-config-app.yaml → applies MetalLB L2 config
      ├── cluster-config-app.yaml → applies cert-manager issuers + namespaces
      ├── docker-storage-app.yaml → deploys private container registry
      ├── homepage-app.yaml       → deploys cluster dashboard
      ├── databases-app.yaml      → watches databases/ directory
      ├── applications-app.yaml   → watches workloads/ directory
      ├── metrics-app.yaml        → deploys observability stack
      ├── localstack-app.yaml     → deploys LocalStack (AWS emulation)
      ├── httpbin-app.yaml        → deploys httpbin (HTTP testing)
      └── rancher-app.yaml        → deploys Rancher cluster management
```

## Adding a New Top-Level Application

1. Create `bootstrap/<name>-app.yaml` as an ArgoCD `Application` resource.
2. Commit and push — the `infra` App-of-Apps auto-discovers it.
3. ArgoCD will begin syncing the new Application on next reconciliation.

## Template

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: <name>
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: 'https://github.com/MrPickle311/titan-gitops.git'
    targetRevision: HEAD
    path: <path-to-manifests>
  destination:
    server: 'https://kubernetes.default.svc'
    namespace: <target-namespace>
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

