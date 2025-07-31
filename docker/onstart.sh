#!/bin/bash

# Redirect all output from this script to a log file for easy debugging.
exec > /root/onstart.log 2>&1

set -e

echo "--- Starting onstart.sh script ---"

# --- Run Non-Critical Setup in Background ---
# This entire block runs as a background process.
# If it fails, it will not stop the SSH server from starting.
(
    echo "[+] Persisting Hugging Face token to /etc/environment..."
    echo "HUGGING_FACE_TOKEN='${HUGGING_FACE_TOKEN}'" >> /etc/environment
    echo "[+] Token persisted."

    echo "[+] Logging into Hugging Face CLI in the background..."
    huggingface-cli login --token "${HUGGING_FACE_TOKEN}"
    echo "[+] Hugging Face login command finished."

    # This is the flag your script will check for. It's only created after
    # the background tasks are complete.
    touch /root/setup_success
    echo "[+] Setup success flag created."
) &

# --- Start Critical Service in Foreground ---
# This is the most important command. It starts the SSH server in the foreground,
# which keeps the container alive and makes it accessible.
# It runs immediately and does not wait for the background tasks.
echo "[+] Starting SSH daemon in foreground..."
/usr/sbin/sshd -D