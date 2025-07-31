#!/bin/bash
# connect_vscode.sh: Connects VS Code to the last pod created.
# Final Version: Dynamically updates ~/.ssh/config for robust connections.
set -e
set -o pipefail

# --- Configuration ---
SSH_USER="root"
REMOTE_FOLDER="/workspace"
HOST_ALIAS="runpod-dynamic-pod" # An alias for the SSH config entry
SSH_CONFIG_PATH="$HOME/.ssh/config"
API_URL="https://api.runpod.io/graphql?api_key=${RUNPOD_API_KEY}"
POD_ID_FILE=".runpod_last_pod_id"
MAX_WAIT_SECONDS=180

# --- Input Validation ---
if [ ! -f "$POD_ID_FILE" ]; then
    echo "❌ Error: Pod ID file not found. Run './create_pod.sh' first." >&2
    exit 1
fi
POD_ID=$(cat "$POD_ID_FILE")

# --- Function to get SSH Details with Polling ---
get_ssh_details() {
    # This function remains the same as the last version.
    local pod_id="$1"
    echo "🔍 Waiting for SSH details for Pod ID: ${pod_id}..." >&2
    local start_time=$(date +%s)
    while true; do
        local query_payload
        query_payload=$(printf '{"query": "query Pod { pod(input: {podId: \\"%s\\"}) { runtime { ports { ip privatePort publicPort type } } } }"}' "$pod_id")
        local ssh_info
        ssh_info=$(curl -s -X POST -H "Content-Type: application/json" -d "$query_payload" "$API_URL" | jq -c '(.data.pod.runtime.ports // [])[] | select(.privatePort == 22) | {host: .ip, port: .publicPort}')
        if [[ -n "$ssh_info" ]]; then
            echo "$ssh_info"
            return
        fi
        local current_time=$(date +%s)
        local elapsed_time=$((current_time - start_time))
        if [ $elapsed_time -ge $MAX_WAIT_SECONDS ]; then
            echo "❌ Error: Timed out waiting for SSH details." >&2
            exit 1
        fi
        printf '.' >&2
        sleep 5
    done
}

# --- Main Execution ---
echo "🚀 Starting VS Code connection process for Pod ID: ${POD_ID}..."
ssh_details=$(get_ssh_details "$POD_ID")
SSH_HOST=$(echo "$ssh_details" | jq -r '.host')
SSH_PORT=$(echo "$ssh_details" | jq -r '.port')
echo "" 
echo "✅ SSH details found:"
echo "   - Host: ${SSH_HOST}"
echo "   - Port: ${SSH_PORT}"

# --- NEW: Dynamically Update SSH Config ---
echo "⚙️  Updating SSH configuration for alias '${HOST_ALIAS}'..."

# Create config file if it doesn't exist
touch "$SSH_CONFIG_PATH"
# Remove any existing configuration for our alias to avoid duplicates
sed -i.bak "/^Host ${HOST_ALIAS}$/,/^[ \t]*Host[ \t\n]/ s/^.*$//; /^[ \t]*$/d" "$SSH_CONFIG_PATH"

# Add the new, updated configuration block to the top of the file
printf "Host ${HOST_ALIAS}\n    HostName ${SSH_HOST}\n    User ${SSH_USER}\n    Port ${SSH_PORT}\n    IdentityFile ~/.ssh/id_ed25519\n    StrictHostKeyChecking no\n    UserKnownHostsFile /dev/null\n\n" | cat - "$SSH_CONFIG_PATH" > temp_config && mv temp_config "$SSH_CONFIG_PATH"
chmod 600 "$SSH_CONFIG_PATH"

echo "✅ SSH configuration updated."

# --- Connect using the Alias ---
# This URI is simpler and more reliable as it uses the alias from ~/.ssh/config
VSCODE_URI="vscode-remote://ssh-remote+${HOST_ALIAS}${REMOTE_FOLDER}"

echo "💻 Launching VS Code..."
code --folder-uri "$VSCODE_URI"

echo "🎉 VS Code connection initiated."