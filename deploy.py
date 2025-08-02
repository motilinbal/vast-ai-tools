import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import vastai_sdk

# --- Configuration ---
DOCKER_IMAGE = "motilin/huggingface-pytorch-ml:latest"
GPU_TYPE = "RTX_A5000"
GPU_COUNT = 1
MAX_PRICE = 0.3
DISK_SPACE_GB = 70
VASTAI_API_KEY = os.getenv("VASTAI_API_KEY")
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
SSH_PUBLIC_KEY_PATH = os.path.expanduser("~/.ssh/id_ed25519.pub")
SSH_CONFIG_ALIAS = "vast-ai-dev"
POLL_TIMEOUT_MINS = 5
POLL_INTERVAL_SECS = 20

# --- onstart_cmd for HF login and VS Code cleanup ---
ONSTART_CMD = """
#!/bin/bash
set -e
exec > /root/onstart.log 2>&1
echo "--- Starting onstart script ---"
# Proactively remove old VS Code server cache to prevent connection hangs.
echo "[+] Removing previous .vscode-server directory to ensure a clean start..."
rm -rf /root/.vscode-server
echo "[+] Logging into Hugging Face CLI..."
huggingface-cli login --token "${HUGGING_FACE_TOKEN}" --add-to-git-credential
echo "[+] Hugging Face login complete."
"""

def find_and_create_instance(client: vastai_sdk.VastAI) -> Optional[int]:
    print(f"🔍 Searching for a {GPU_TYPE} under ${MAX_PRICE}/hr...")
    query = f"num_gpus={GPU_COUNT} gpu_name={GPU_TYPE} rented=False verified=True dph_total<={MAX_PRICE}"
    order = "score-"
    try:
        offers = client.search_offers(query=query, order=order, type='on-demand')
        if not offers:
            print(f"❌ No matching instances found.", file=sys.stderr)
            return None
        best_offer = offers[0]
        offer_id = best_offer['id']
        price = best_offer.get('dph_total', 'N/A')
        print(f"✅ Found offer {offer_id} for ${price}/hr. Creating instance...")
        # Read public key content
        with open(SSH_PUBLIC_KEY_PATH, "r") as f:
            public_key = f.read().strip()
        # Environment variables and port mappings as string
        env_str = f'-e HUGGING_FACE_TOKEN="{HF_TOKEN}" -e SSH_PUB_KEY="{public_key}" -p 8080'
        result = client.create_instance(
            id=offer_id,
            image=DOCKER_IMAGE,
            disk=float(DISK_SPACE_GB),
            env=env_str,  # Pass env and ports as string
            onstart_cmd=ONSTART_CMD,
            jupyter=False,
            runtype="ssh",  # Use "ssh" runtype for Vast.ai's SSH setup + onstart_cmd
            direct=True
        )
        if result and result.get("success"):
            instance_id = result.get("new_contract")
            print(f"🚀 Instance {instance_id} creation initiated.")
            return instance_id
        else:
            print(f"❌ Instance creation failed: {result.get('msg', 'Unknown error')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"❌ Error during instance creation: {e}", file=sys.stderr)
        return None

def poll_for_ssh_readiness(client: vastai_sdk.VastAI, instance_id: int) -> Optional[Dict[str, Any]]:
    print(f"⏳ Waiting for instance {instance_id} to become fully ready...")
    start_time = time.time()
    timeout_seconds = POLL_TIMEOUT_MINS * 60
    while time.time() - start_time < timeout_seconds:
        try:
            instance = client.show_instance(id=instance_id)
            if not instance:
                time.sleep(POLL_INTERVAL_SECS)
                continue
            ssh_host = instance.get("public_ipaddr")
            ports = instance.get("ports", {})
            port_info = ports.get("22/tcp")
            if ssh_host and port_info:
                ssh_port = port_info[0].get("HostPort")
                connection_type = "direct"
            else:
                ssh_host = instance.get("ssh_host")
                ssh_port = instance.get("ssh_port")
                connection_type = "proxy"
            if ssh_host and ssh_port:
                print(f" API reports {connection_type} connection ready at {ssh_host}:{ssh_port}. Verifying...")
                try:
                    command = (
                        f"ssh -p {ssh_port} -o ConnectTimeout=10 -o BatchMode=yes "
                        f"-o StrictHostKeyChecking=no root@{ssh_host} echo 'SSH_OK'"
                    )
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
                    if result.returncode == 0 and "SSH_OK" in result.stdout:
                        print(f"✅ SSH Connection Verified! Instance is fully ready.")
                        return {"ssh_host": ssh_host, "ssh_port": ssh_port}
                    else:
                        print(f" SSH connection failed. Retrying... (stdout: {result.stdout}, stderr: {result.stderr})")
                except subprocess.TimeoutExpired:
                    print(f" SSH command timed out. Retrying...")
            actual_status = instance.get("actual_status", "")
            if "error" in (instance.get("status_msg") or "").lower():
                print(f"❌ Instance entered failed state: {instance.get('status_msg')}")
                return None
            print(f" Current status: {actual_status or 'initializing'} | Waiting for SSH handshake...")
            time.sleep(POLL_INTERVAL_SECS)
        except Exception as e:
            print(f"⚠️ Warning during polling: {e}. Retrying...", file=sys.stderr)
            time.sleep(POLL_INTERVAL_SECS)
    print(f"⏰ Timed out waiting for instance to become fully ready.", file=sys.stderr)
    return None

def update_ssh_config(alias: str, hostname: str, port: int, user: str = "root"):
    print("📝 Updating local SSH configuration...")
    ssh_dir = Path.home() / ".ssh"
    config_d_dir = ssh_dir / "config.d"
    instance_config_file = config_d_dir / f"vast-ai-{alias}"
    config_d_dir.mkdir(exist_ok=True)
    config_content = f"""
Host {alias}
    HostName {hostname}
    User {user}
    Port {port}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ConnectTimeout 10
"""
    instance_config_file.write_text(config_content)
    print(f" ✅ SSH config written to: {instance_config_file}")

def retrieve_instance_logs(client: vastai_sdk.VastAI, instance_id: int):
    print(f"🔬 Retrieving internal logs for instance {instance_id} via API...")
    try:
        log_content = client.logs(INSTANCE_ID=instance_id)
        print("\n" + "="*25 + " INSTANCE LOGS " + "="*25)
        print(log_content or "Logs were empty.")
        print("="*60)
    except Exception as e:
        print(f" ❌ An error occurred while fetching logs: {e}", file=sys.stderr)

def main():
    if not VASTAI_API_KEY:
        print("Error: VASTAI_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)
    client = vastai_sdk.VastAI(api_key=VASTAI_API_KEY)
    try:
        with open(SSH_PUBLIC_KEY_PATH, "r") as f:
            public_key = f.read()
        client.create_ssh_key(ssh_key=public_key)
        print("🔑 SSH key ensured on Vast.ai account.")
    except Exception as e:
        print(f"⚠️ Could not add SSH key (it may already exist): {e}")
    instance_id = None
    try:
        instance_id = find_and_create_instance(client)
        if not instance_id: sys.exit(1)
        connection_details = poll_for_ssh_readiness(client, instance_id)
        if connection_details:
            update_ssh_config(
                alias=SSH_CONFIG_ALIAS,
                hostname=connection_details["ssh_host"],
                port=connection_details["ssh_port"]
            )
            print("\n" + "="*60)
            print("🎉 SUCCESS! Your Vast.ai instance is fully configured and verified.")
            print("To connect, use 'Remote-SSH: Connect to Host...' in VS Code")
            print(f"and select the host alias: '{SSH_CONFIG_ALIAS}'")
            print("="*60)
        else:
            raise RuntimeError("Instance failed to become ready.")
    except Exception as e:
        print(f"\n💥 Workflow failed: {e}", file=sys.stderr)
        if instance_id:
            retrieve_instance_logs(client, instance_id)
            print(f"🔥 Destroying failed instance {instance_id}...")
            try:
                client.destroy_instance(id=instance_id)
                print(f"✅ Instance {instance_id} destroyed.")
            except Exception as destroy_e:
                print(f"❌ Failed to destroy instance {instance_id}: {destroy_e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()