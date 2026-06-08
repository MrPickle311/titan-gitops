# talos/

Talos Linux machine configuration files. Applied directly via `talosctl` against the nodes — **not** managed by ArgoCD.

## Files

| File | Purpose |
|---|---|
| `controlplane.yaml` | Full Talos machine config for the control plane node |
| `worker.yaml` | Full Talos machine config for worker nodes |
| `cp.yaml` | Minimal control plane bootstrap config used during initial cluster creation |
| `patch-node1.yaml` | Node-specific hostname and network patch for node1 |
| `patch-node2.yaml` | Node-specific hostname and network patch for node2 |
| `patch-worker1.yaml` | Node-specific hostname and network patch for worker1 |
| `patch-storage.yaml` | Enables OpenEBS hostpath requirements at OS level |
| `patch-local-docker-registry.yaml` | Configures Talos container runtime to trust `registry.homelab` without public TLS verification |
| `talosconfig` | `talosctl` client config — contains cluster endpoint and client certificates |

## Applying Changes

```bash
# Apply config to a specific node
talosctl apply-config --nodes <NODE_IP> --file controlplane.yaml

# Apply a patch
talosctl patch mc --nodes <NODE_IP> --patch @patch-node1.yaml

# Upgrade Talos on a node
talosctl upgrade --nodes <NODE_IP> --image ghcr.io/siderolabs/installer:<VERSION>
```

## Security Warning

`talosconfig`, `controlplane.yaml`, and `worker.yaml` contain TLS certificates and machine secrets generated during cluster bootstrapping.

**These files must never be committed to a public repository.**

Recommended approaches for secure storage:
- Encrypt with [SOPS + age](https://github.com/getsops/sops) before committing
- Store in a secrets manager (Vault, 1Password, Bitwarden) and reference from CI/CD
- At minimum, keep the repository private
