# infrastructure/

Foundational cluster resources managed by ArgoCD. Each subdirectory has its own ArgoCD Application registered in `bootstrap/`.

## Components

### cluster-config/
Sets up the internal PKI chain using cert-manager:
- `selfsigned-bootstrap-issuer` — self-signed `ClusterIssuer` used only to create the root CA certificate
- `homelab-ca-cert` — the root CA Certificate stored in `homelab-ca-secret`
- `homelab-ca-issuer` — `ClusterIssuer` backed by the root CA; used by all ingresses via `cert-manager.io/cluster-issuer: homelab-ca-issuer`

The two-step chain (self-signed → CA → workload certs) avoids bootstrapping issues with cert-manager.

### docker-storage/
Self-hosted OCI-compliant container registry at `registry.homelab`:
- Registry backed by a 50Gi OpenEBS PVC
- Registry UI for image browsing
- TLS terminated by homelab CA
- All workload images are pushed here before deployment

### metallb-config/
MetalLB Layer 2 advertisement config:
- `IPAddressPool`: `10.0.0.200–10.0.0.254`
- `L2Advertisement`: announces assigned IPs via ARP on the local network

### homepage/
Cluster dashboard at `homepage.homelab` (gethomepage.dev):
- Read-only access to Kubernetes API via `ClusterRole` / `ClusterRoleBinding`
- Config managed via ConfigMaps in `homepage/config/`

### applications-namespace.yaml
Declares the `applications` namespace with `privileged` pod security enforcement. Required because JVM services use `JAVA_TOOL_OPTIONS` with Java agents, which requires elevated container privileges.

### kustomization.yaml
Kustomize entry point for the `cluster-config` ArgoCD Application. Only includes resources that have no dedicated ArgoCD Application. Adding a resource here that already has its own Application causes `SharedResourceWarning`.
