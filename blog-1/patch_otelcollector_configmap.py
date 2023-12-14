HELP = """
# Setup:
With a working otel demo running, get the otel-collector's configmap and your
CCO credentials:

## ConfigMap
Get the configmap from the k8s cluster:
```sh
pip install pyyaml
kubectl get configmap my-otel-demo-otelcol -o yaml > my-otel-demo-otelcol.yaml
```

## Credentials
Get `collectors-values.yaml` from an admin.

# Usage example
```sh
python patch_otelcollector_configmap.py \\
    my-otel-demo-otelcol.yaml \\
    credentials/collectors-values.yaml \\
    5c187138-8a73-4982-b9a5-a8bcc8681b5f
```
## Args
- my-otel-demo-otelcol.yaml is the otel-collector's configmap
- credentials/collectors-values.yaml contains your CCO credentials
- 5c18... is your CCO tenant ID
"""

import sys, yaml
from pathlib import Path

# Get the filenames from the command line
try:
    cmfn, credfn, tenant = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
except:
    print(HELP)
    exit(1)

print("Got these args:", cmfn, credfn, tenant, sep='\n\t - ')

with open(cmfn) as f:
    _configmap = yaml.load(f, Loader=yaml.FullLoader)

with open(credfn) as f:
    creds = yaml.load(f, Loader=yaml.FullLoader)

# Load the credentials
clientId = creds['appdynamics-otel-collector']['clientId']
clientSecret = creds['appdynamics-otel-collector']['clientSecret']
endpoint = creds['appdynamics-otel-collector']['endpoint']
tokenUrl = creds['appdynamics-otel-collector']['tokenUrl']
print(f"Loaded creds for cluster: '{creds['global']['clusterName']}'", clientId, clientSecret, endpoint, tokenUrl, sep='\n\t - ')

# Load the ConfigMap from the otel demo
cm = yaml.load(_configmap['data']['relay'], Loader=yaml.FullLoader)

# 1. Add the credentials to the ConfigMap
# 2. Configure the oauth2client extension and otlphttp exporter
if 'oauth2client' in cm['extensions']:
    print("oauth2client already in configmap, don't need to patch, aborting.")
    exit(0)
cm['extensions']['oauth2client'] = {
    'client_id': clientId,
    'client_secret': clientSecret,
    'token_url': tokenUrl,
}
cm['exporters']['otlphttp'] = {
    "auth": {
        "authenticator": "oauth2client"
    },
    "traces_endpoint": endpoint + "/v1/trace",
    "metrics_endpoint": endpoint + "/v1/metrics"
}
cm['service']['extensions'].append('oauth2client')
cm['service']['pipelines']['traces']['exporters'].append('otlphttp')
cm['service']['pipelines']['metrics']['exporters'].append('otlphttp')

# Write the patched configmap to a file
outfn = cmfn.with_name(cmfn.stem + '-patched.yaml')
with open(outfn, 'w') as f:
    yaml.dump(cm, f)

FOLLOW_UP = f"""```
kubectl create configmap my-otel-demo-otelcol \\
    -n my-otel-demo-ns \\
    --from-file=relay={outfn} \\
    -o yaml \\
    --dry-run \\
    | kubectl apply -f -
```"""
print('SUCCESS')
print(f"Wrote configmap to '{outfn}'.",
      "Now apply it with:",
      FOLLOW_UP,
      sep="\n")
