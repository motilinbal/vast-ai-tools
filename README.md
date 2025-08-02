# Vast.ai GPU Instance Provisioning for ML Development

This repository provides a complete, automated workflow for provisioning GPU-enabled development environments on Vast.ai. It includes tools to deploy instances with pre-configured Docker images (including ML libraries like diffusers and transformers), set up secure SSH access, integrate with VS Code Remote-SSH, and handle file transfers between local and remote machines.

Key features:
- Programmatic instance creation via Python ([`deploy.py`](deploy.py)).
- Custom Docker image with SSH server and ML dependencies.
- Automatic Hugging Face CLI login for gated models.
- VS Code Remote-SSH compatibility with auto-installed extensions.
- Efficient file/folder transfer utilities ([`file_transfer.py`](file_transfer.py)).

## Prerequisites

- **Accounts and Keys**:
  - Vast.ai account with API key (set as environment variable: `export VASTAI_API_KEY=your_key`).
  - Hugging Face token for gated models (set as `export HUGGING_FACE_TOKEN=your_token`).
  - SSH key pair (default: `~/.ssh/id_ed25519.pub` for public key).

- **Software**:
  - Python 3.8+ with `vastai-sdk` installed (`pip install vastai-sdk`).
  - Docker for building the image.
  - VS Code with Remote-SSH extension (for development integration).
  - rsync (installed on your local machine for file transfers).

- **Environment Variables**: Ensure `VASTAI_API_KEY` and `HUGGING_FACE_TOKEN` are set before running scripts.

## 1. Setting Up the Docker Image

The Docker image is based on `vastai/pytorch:cuda-12.4.1-auto` and includes OpenSSH, ML libraries from [`docker/requirements.txt`](docker/requirements.txt), a hardened SSH config, and an entrypoint script for initialization.

### Steps:
1. **Clone the Repository**:
   ```
   git clone https://your-repo-url.git
   cd your-repo-name
   ```

2. **Build the Image**:
   Run the following command in the repository root (where [`docker/Dockerfile`](docker/Dockerfile), [`docker/requirements.txt`](docker/requirements.txt), [`docker/hardened_sshd_config`](docker/hardened_sshd_config), and [`docker/entrypoint.sh`](docker/entrypoint.sh) are located):
   ```
   docker build -t motilin/huggingface-pytorch-ml:latest -f docker/Dockerfile .
   ```
   - This installs dependencies, sets up SSH, and prepares the workspace.

3. **Push to Docker Hub** (or your registry):
   ```
   docker push motilin/huggingface-pytorch-ml:latest
   ```
   - Ensure you're logged in (`docker login`) with credentials for your Docker Hub account (replace `motilin` with your username if needed).

The image exposes ports 22 (SSH) and 8080 (for forwarding, e.g., Jupyter). It's ready for Vast.ai deployment once pushed.

### Docker Image Details

The Docker image includes:

- **Base Image**: `vastai/pytorch:cuda-12.4.1-auto`
- **SSH Configuration**: Hardened SSH server with TCP forwarding enabled for VS Code Remote-SSH
- **ML Dependencies**: Comprehensive ML libraries including PyTorch, Transformers, Diffusers, and more
- **Entry Point**: [`docker/entrypoint.sh`](docker/entrypoint.sh) handles SSH key setup, Hugging Face login, and starts the SSH daemon
- **Onstart Script**: [`docker/onstart.sh`](docker/onstart.sh) provides background setup tasks while keeping the container running

## 2. Setting Up VS Code for Remote Extensions

To automatically install essential extensions (Python, Jupyter, Jupyter Renderers) on remote instances via Remote-SSH, configure your local VS Code settings.

### Steps:
1. **Open VS Code Settings**:
   - Press `Ctrl + ,` (or Cmd + , on macOS) to open settings.
   - Search for "settings.json" and click "Edit in settings.json".

2. **Add Default Remote Extensions**:
   Update `~/.config/Code/User/settings.json` (or equivalent on your OS) with:
   ```json
   {
       "remote.SSH.defaultExtensions": [
           "ms-python.python",
           "ms-toolsai.jupyter",
           "ms-toolsai.jupyter-renderers"
       ]
   }
   ```
   - This ensures the extensions install automatically on first SSH connection to any remote host.

3. **Verify Marketplace Access** (if needed):
   - If extensions fail to install (e.g., marketplace issues), ensure VS Code uses the official marketplace (default behavior).

4. **Connect and Test**:
   - After deploying an instance (see below), use Remote-SSH to connect.
   - Extensions should auto-install; reload the remote window if prompted.

This setup eliminates manual extension installation for ephemeral instances.

## 3. Using deploy.py

[`deploy.py`](deploy.py) automates finding, creating, and verifying a Vast.ai instance with your custom Docker image. It polls for readiness, updates local SSH config, and supports direct SSH/VS Code integration.

### Configuration Options

The script includes several configurable constants at the top of the file:

- `DOCKER_IMAGE`: Docker image to use (default: "motilin/huggingface-pytorch-ml:latest")
- `GPU_TYPE`: GPU type to search for (default: "RTX_A5000")
- `GPU_COUNT`: Number of GPUs (default: 1)
- `MAX_PRICE`: Maximum price per hour in USD (default: 0.3)
- `DISK_SPACE_GB`: Disk space in GB (default: 70)
- `SSH_CONFIG_ALIAS`: SSH alias to create (default: "vast-ai-dev")
- `POLL_TIMEOUT_MINS`: Minutes to wait for instance readiness (default: 5)
- `POLL_INTERVAL_SECS`: Seconds between polling attempts (default: 20)

### Steps:
1. **Set Environment Variables**:
   ```
   export VASTAI_API_KEY=your_vastai_api_key
   export HUGGING_FACE_TOKEN=your_hf_token
   ```

2. **Run the Script**:
   ```
   python deploy.py
   ```
   - It searches for an RTX A5000 under $0.3/hr (configurable in script).
   - Creates the instance with your Docker image, HF token, and onstart commands (e.g., HF login, VS Code cleanup).
   - Polls until SSH is ready (up to 5 minutes).
   - Updates `~/.ssh/config.d/vast-ai-vast-ai-dev` with connection details (alias: `vast-ai-dev`).

3. **Connect via VS Code**:
   - Open VS Code.
   - Press Ctrl+Shift+P > "Remote-SSH: Connect to Host..." > Select "vast-ai-dev".
   - The workspace opens remotely; extensions auto-install if configured.

4. **Customization**:
   - Edit constants like `GPU_TYPE`, `MAX_PRICE`, `DISK_SPACE_GB` in [`deploy.py`](deploy.py:11-21).
   - If deployment fails, logs are retrieved automatically.

The instance is billed hourly; destroy via Vast.ai dashboard or SDK when done.

### Deployment Workflow

The [`deploy.py`](deploy.py) script follows this workflow:

1. **SSH Key Management**: Ensures your SSH public key is added to your Vast.ai account
2. **Instance Search**: Finds available GPU instances matching your criteria
3. **Instance Creation**: Launches a new instance with your Docker image and configuration
4. **Readiness Polling**: Continuously checks if the instance is ready for SSH connections
5. **SSH Configuration**: Updates your local SSH config with the connection details
6. **Error Handling**: Automatically retrieves logs and cleans up failed instances

## 4. Using file_transfer.py

[`file_transfer.py`](file_transfer.py) provides utilities for transferring files/folders between your local machine and the Vast.ai instance using rsync over SSH. It parses your SSH config to auto-detect hosts and uses the alias (e.g., "vast-ai-dev") for seamless transfers.

### Available Functions

The module provides four main functions:

- `upload_file(local_path, remote_path)`: Upload a single file to the remote instance
- `download_file(remote_path, local_path)`: Download a single file from the remote instance
- `upload_folder(local_dir, remote_dir)`: Upload a folder recursively to the remote instance
- `download_folder(remote_dir, local_dir)`: Download a folder recursively from the remote instance

### Steps:
1. **Import and Use**:
   - In your Python script:
     ```python
     from file_transfer import upload_file, download_file, upload_folder, download_folder
     
     # Example: Upload a file
     upload_file("local_file.txt", "/workspace/remote_file.txt")
     
     # Download a folder
     download_folder("/workspace/remote_dir", "local_dir")
     ```
   - On first run (if multiple hosts), it prompts for selection. Subsequent calls reuse if single host.

2. **How It Works**:
   - [`retrieve_ssh_details()`](file_transfer.py:9): Parses `~/.ssh/config` and `config.d/*` for hosts. Prompts if >1; errors if 0.
   - [`upload_file()`](file_transfer.py:106)/[`download_file()`](file_transfer.py:157): Transfers single files.
   - [`upload_folder()`](file_transfer.py:205)/[`download_folder()`](file_transfer.py:255): Recursively transfers directories (syncs contents).
   - All use rsync for efficiency; supports progress display.

3. **Requirements**:
   - rsync installed locally.
   - SSH config updated via [`deploy.py`](deploy.py) (for alias like "vast-ai-dev").

This enables easy data syncing without manual SSH commands.

### SSH Host Detection

The [`retrieve_ssh_details()`](file_transfer.py:9) function intelligently detects available SSH hosts by:

1. Reading the main SSH config file at `~/.ssh/config`
2. Parsing any included config files (including wildcard patterns like `config.d/*`)
3. Collecting all unique host aliases (excluding wildcard hosts)
4. Prompting for selection if multiple hosts are found
5. Returning the selected alias for use in file transfer operations

## Troubleshooting

### Common Issues

- **Connection Issues**: Ensure SSH key is added to Vast.ai account; check firewall/port forwarding.
- **HF Login Fails**: Verify token has read access; check `/root/onstart.log` on instance.
- **Slow Inference**: Use quantization/optimizations as discussed in prior conversations.
- **Extension Install Fails**: Confirm VS Code marketplace access; manually install if needed.

### Debugging Tips

1. **Check Instance Logs**:
   - SSH into the instance and view `/root/onstart.log` for startup issues
   - The [`deploy.py`](deploy.py) script automatically retrieves logs if deployment fails

2. **Verify SSH Configuration**:
   - Check `~/.ssh/config.d/vast-ai-vast-ai-dev` for correct connection details
   - Test SSH connection manually: `ssh vast-ai-dev`

3. **Docker Image Issues**:
   - Ensure the Docker image was built and pushed correctly
   - Verify the image name in [`deploy.py`](deploy.py:11) matches your pushed image

4. **File Transfer Problems**:
   - Ensure rsync is installed locally: `rsync --version`
   - Check that the SSH host alias is correctly configured
   - Verify file paths and permissions on both local and remote systems

### Getting Help

For issues, open a GitHub issue or contact Vast.ai support. Contributions welcome!