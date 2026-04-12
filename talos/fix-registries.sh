#!/bin/bash
set -e

export TALOSCONFIG=/home/damian/homelab/talosconfig
NODES=("10.0.0.50" "10.0.0.52" "10.0.0.53")
WORKDIR=$(mktemp -d -p /home/damian/homelab/titan-gitops)

for NODE in "${NODES[@]}"; do
    echo "=== Processing node $NODE ==="
    
    # Extract the raw machine config
    talosctl -n "$NODE" get mc v1alpha1 -o yaml | \
        sed -n '/^spec: |/,/^---$/p' | \
        sed '1s/^spec: |//' | \
        sed '/^---$/d' | \
        sed 's/^    //' > "$WORKDIR/mc-$NODE.yaml"
    
    # Replace the registries section with only the ClusterIP mirror
    python3 -c "
import yaml, sys

with open('$WORKDIR/mc-$NODE.yaml') as f:
    docs = list(yaml.safe_load_all(f))

for doc in docs:
    if doc and doc.get('version') == 'v1alpha1' and 'machine' in doc:
        doc['machine']['registries'] = {
            'mirrors': {
                'registry.homelab': {
                    'endpoints': ['http://10.96.100.1']
                }
            }
        }

with open('$WORKDIR/mc-$NODE-fixed.yaml', 'w') as f:
    yaml.dump_all(docs, f, default_flow_style=False)
"
    
    echo "Fixed config for $NODE:"
    grep -A6 "mirrors:" "$WORKDIR/mc-$NODE-fixed.yaml" | head -8
    echo ""
    
    # Apply the fixed config
    talosctl -n "$NODE" apply-config --file "$WORKDIR/mc-$NODE-fixed.yaml"
    
    echo "=== Done with node $NODE ==="
    echo ""
done

rm -rf "$WORKDIR"
echo "All nodes updated!"
