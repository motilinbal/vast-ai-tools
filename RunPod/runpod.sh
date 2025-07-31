#!/bin/bash

# --- Pod Creation and Setup Script ---

echo "🚀 Starting a new RunPod instance..."

# Create the pod using your custom image and save the output
# This command returns a JSON object with the new pod's details
POD_INFO=$(runpodctl create pod \
    --name "dev-pod" \
    --gpuType "NVIDIA GeForce RTX A5000" \
    --imageName "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04" \
    --containerDiskSize 70 \
    --networkVolumeId "wm2njaqe19" \
    --ports "22/tcp" \
    --env HF_TOKEN=${HF_TOKEN} \
    --env HF_HOME=/workspace/.cache \
    --env TMPDIR=/workspace/tmp)

# Check if the pod was created successfully
if [ -z "$POD_INFO" ]; then
    echo "❌ Pod creation failed."
    exit 1
fi

# Extract the pod ID from the JSON output
POD_ID=$(echo $POD_INFO | jq -r '.id')
echo "✅ Pod created successfully with ID: $POD_ID"

echo "⏳ Waiting for pod to initialize..."
# This simple loop waits until the pod is running and SSH is ready
until runpodctl ssh $POD_ID -- "echo 'Pod is ready'" > /dev/null 2>&1; do
    printf '.'
    sleep 2
done
echo ""

echo "📦 Sending local scripts to the pod..."
# Send your Python script to the /workspace directory on the pod
runpodctl send $POD_ID run_flux.py /workspace/

echo "✅ Pod is ready and scripts are copied."
echo "---"
echo "To connect directly in your terminal, run:"
echo "runpodctl ssh $POD_ID"
echo ""
echo "To connect with VS Code, follow the instructions below."

