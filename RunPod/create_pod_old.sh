#!/bin/bash
# ==============================================================================
# Final, Production-Ready RunPod Creation Script
# ==============================================================================
# This script performs pre-flight checks for GPU price and availability in a
# specific datacenter before creating a pod with all required configurations.
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e
# The return value of a pipeline is the status of the last command to exit with a non-zero status.
set -o pipefail

# --- Configuration ---
# CRITICAL: Set these three variables before running the script.
export DATACENTER_ID="EU-SE-1"
export NETWORK_VOLUME_ID="wm2njaqe19"
export MAX_HOURLY_PRICE="0.30"

# --- Pod Settings ---
POD_NAME="auto-flux-pod-$(date +%s)"
GPU_TYPE="NVIDIA RTX A5000"
DOCKER_IMAGE="runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"
CONTAINER_DISK_GB=80

# --- GraphQL API and Authentication ---
# This script requires the RUNPOD_API_KEY to be set as a local environment variable.
API_URL="https://api.runpod.io/graphql?api_key=${RUNPOD_API_KEY}"

# --- Function to check GPU stock and price ---
check_gpu_availability() {
    local gpu_name="$1"
    local datacenter_id="$2"
    echo "🔍 Verifying price and stock for '${gpu_name}' in datacenter '${datacenter_id}'..." >&2

    local query_payload
    query_payload=$(printf '{"query": "query GpuAvailability { gpuTypes(input: {id: \\"%s\\"}) { id displayName lowestPrice(input: {gpuCount: 1, dataCenterId: \\"%s\\"}) { uninterruptablePrice stockStatus } } }"}' "$gpu_name" "$datacenter_id")

    local api_response
    api_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$query_payload" \
        "$API_URL")

    local price
    price=$(echo "$api_response" | jq -r '.data.gpuTypes[0].lowestPrice.uninterruptablePrice')
    local stock_status
    stock_status=$(echo "$api_response" | jq -r '.data.gpuTypes[0].lowestPrice.stockStatus')

    # --- Price Check ---
    if [[ -z "$price" || "$price" == "null" ]]; then
        echo "❌ Error: Could not retrieve price. The GPU may not be available in the specified datacenter." >&2
        exit 1
    fi
    echo "💵 Current on-demand price is \$${price}/hr."
    if (( $(echo "$price > $MAX_HOURLY_PRICE" | bc -l) )); then
        echo "❌ Price check failed. Current price exceeds maximum allowed price." >&2
        exit 1
    fi
    echo "✅ Price check passed."

    # --- Stock Check ---
    if [[ -z "$stock_status" || "$stock_status" == "null" || "$stock_status" == "OUT_OF_STOCK" ]]; then
        echo "❌ Verification failed. GPU '${gpu_name}' is not in stock in datacenter '${datacenter_id}'. Current status: ${stock_status:-Not Available}" >&2
        exit 1
    fi
    echo "✅ Stock confirmed for ${gpu_name}. Status: ${stock_status}"
}

# --- Main Execution ---
# 1. Validation
if [[ -z "${RUNPOD_API_KEY:-}" ]]; then
    echo "❌ Error: RUNPOD_API_KEY is not set in your local environment." >&2
    exit 1
fi
echo "🚀 Starting RunPod creation process..."

# 2. Price and Stock Verification
check_gpu_availability "$GPU_TYPE" "$DATACENTER_ID"

# 3. Create the Pod
echo "🛠️ Creating pod '${POD_NAME}'..."

# CORRECTED: Replaced `jq` with `awk` to parse the plain text output.
pod_id=$(runpodctl create pod \
    --name "$POD_NAME" \
    --gpuType "$GPU_TYPE" \
    --imageName "$DOCKER_IMAGE" \
    --secureCloud \
    --containerDiskSize "$CONTAINER_DISK_GB" \
    --networkVolumeId "${NETWORK_VOLUME_ID}" \
    --volumePath "/workspace" \
    --ports "22/tcp" \
    --env "HF_HOME=/workspace/.cache" \
    --env "TMPDIR=/workspace/tmp" \
    --env "HF_TOKEN={{ RUNPOD_SECRET_HF_TOKEN }}" | awk -F '"' '{print $2}')

if [[ -z "$pod_id" ]]; then
    echo "❌ Error: Pod creation failed or could not parse Pod ID." >&2
    exit 1
fi

# Save the new pod ID to a file for the connect script to use.
echo "$pod_id" > .runpod_last_pod_id

echo "✅ Pod creation successful!"
echo "🎉 New Pod ID: ${pod_id}"
echo "   Run './connect_vscode.sh' to connect."