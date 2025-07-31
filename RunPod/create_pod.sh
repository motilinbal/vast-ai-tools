#!/bin/bash
#
# create_pod.sh: Deploys a RunPod pod with direct TCP access via the GraphQL API.
# This script requires `jq` to be installed.
# The RUNPOD_API_KEY must be set as an environment variable.
#
set -euo pipefail

# --- Configuration ---
POD_NAME="Automated-SSH-Pod-$(date +%s)"
POD_GPU_TYPE="NVIDIA RTX A5000"
POD_IMAGE="runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"
POD_TCP_PORTS="22/tcp"
POD_CONTAINER_DISK_GB=70
POD_VOLUME_ID="wm2njaqe19" # Your network volume ID

# The full start command from your template, now defined directly in the script.
DOCKER_ARGS=$(cat <<'EOF'
#!/bin/bash
if [ -n "$PUBLIC_KEY" ]; then
  mkdir -p /root/.ssh
  echo "$PUBLIC_KEY" > /root/.ssh/authorized_keys
  chmod 700 /root/.ssh
  chmod 600 /root/.ssh/authorized_keys
fi
ssh-keygen -A
service ssh start
/start.sh
EOF
)

# --- Pre-flight Checks ---
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is not installed. Please install it to continue." >&2
    exit 1
fi
if [[ -z "${RUNPOD_API_KEY:-}" ]]; then
  echo "❌ Error: RUNPOD_API_KEY environment variable is not set." >&2
  exit 1
fi
echo "✅ Prerequisites met."

# --- GraphQL Payload Construction using jq ---
# This method safely builds the JSON payload, avoiding syntax errors.
GRAPHQL_PAYLOAD=$(jq -n \
  --arg name "$POD_NAME" \
  --arg imageName "$POD_IMAGE" \
  --arg gpuTypeId "$POD_GPU_TYPE" \
  --arg ports "$POD_TCP_PORTS" \
  --arg dockerArgs "$DOCKER_ARGS" \
  --arg volumeId "$POD_VOLUME_ID" \
  --argjson containerDiskInGb "$POD_CONTAINER_DISK_GB" \
  '{
    query: "mutation podFindAndDeployOnDemand($input: PodFindAndDeployOnDemandInput!) { podFindAndDeployOnDemand(input: $input) { id name runtime { ports { privatePort publicPort ip } } } }",
    variables: {
      input: {
        name: $name,
        imageName: $imageName,
        gpuTypeId: $gpuTypeId,
        cloudType: "SECURE",
        gpuCount: 1,
        containerDiskInGb: $containerDiskInGb,
        ports: $ports,
        dockerArgs: $dockerArgs,
        networkVolumeId: $volumeId,
        volumeMountPath: "/workspace"
      }
    }
  }')

echo "🚀 Deploying pod with explicit configuration..."

# --- API Execution ---
RESPONSE=$(curl --silent --request POST \
  --header 'content-type: application/json' \
  --header "Authorization: Bearer ${RUNPOD_API_KEY}" \
  --url 'https://api.runpod.io/graphql' \
  --data "$GRAPHQL_PAYLOAD")

# --- Response Handling ---
if [[ $(echo "$RESPONSE" | jq 'has("errors")') == "true" ]]; then
    echo -e "\n❌ Error: API call failed." >&2
    echo "$RESPONSE" | jq . >&2
    exit 1
fi

echo -e "\n✅ Success! Pod deployment initiated."
POD_ID=$(echo "$RESPONSE" | jq -r '.data.podFindAndDeployOnDemand.id')
echo "$POD_ID" > .runpod_last_pod_id
echo "🎉 Pod ID: ${POD_ID}"
echo "SSH connection details will appear in the RunPod dashboard shortly."