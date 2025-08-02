#!/bin/bash
set -e

exec > /root/onstart.log 2>&1

echo "--- Starting entrypoint script ---"

# Proactively remove old VS Code server cache to prevent connection hangs.
echo "[+] Removing previous .vscode-server directory to ensure a clean start..."
rm -rf /root/.vscode-server

# Setup authorized_keys with the provided public key
echo "[+] Setting up SSH authorized_keys..."
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo "$SSH_PUB_KEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# Persist and use Hugging Face token
echo "[+] Logging into Hugging Face CLI..."
huggingface-cli login --token "$HUGGING_FACE_TOKEN"
echo "[+] Hugging Face login complete."

echo "[+] Starting SSH daemon in foreground..."
exec /usr/sbin/sshd -D -e