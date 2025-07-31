# Blueprint: A Robust MLOps Workflow on RunPod

This document provides a complete, step-by-step guide to creating a fast, reliable, and reproducible development environment on RunPod. This workflow solves common issues like startup timeouts, fragile automation, and authentication problems by using a custom Docker image and a streamlined RunPod template.

---

## Phase 1: Create Your Custom Environment on Your Local Machine

In this phase, you will build a custom Docker image that has all of your Python dependencies pre-installed. This is the key to creating a fast-booting pod.

### Step 1: Create the `Dockerfile`

On your local computer, create a new folder for your project. Inside that folder, create a new file named `Dockerfile` (no extension) and paste the following content into it.

```dockerfile
# Start from the official RunPod PyTorch image, which includes CUDA and necessary drivers
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Install all Python dependencies directly into the image layer during the build process
# This avoids slow installations every time the pod starts.
RUN pip install diffusers transformers accelerate sentencepiece protobuf torch --upgrade

# Set the default command that will run when a container starts from this image.
# This script handles essential services like SSH.
CMD ["/start.sh"]
````

### Step 2: Build the Docker Image

Open a terminal in the same directory as your `Dockerfile`. Run the `docker build` command to create your image. Replace `your_username` with your actual Docker Hub username.

```bash
docker build -t your_username/flux-app:latest .
```

### Step 3: Push the Image to a Public Registry

To make your custom image available to RunPod, you must push it to a container registry like Docker Hub.

1.  **Log in** to Docker Hub from your terminal:
    ```bash
    docker login
    ```
2.  **Push** your image:
    ```bash
    docker push your_username/flux-app:latest
    ```
3.  **Make the repository public.** Go to your repository's page on Docker Hub (`https://hub.docker.com/r/your_username/flux-app`), navigate to **Settings**, and change the visibility to **Public**. This is crucial so that RunPod can access and download the image.

-----

## Phase 2: Configure the RunPod Platform

Now you will create a simple and powerful template on RunPod that uses your custom image and handles all configuration automatically.

### Step 4: Create a RunPod Secret for Your Token

To handle authentication securely, store your Hugging Face token as a secret in RunPod.

1.  On the RunPod website, go to **Settings** -\> **Secrets**.
2.  Click **New Secret**.
3.  Set the **Key** to `HF_TOKEN`.
4.  For the **Value**, paste your actual Hugging Face token string (the one that starts with `hf_...`).

### Step 5: Create the Final RunPod Template

Go to **Templates** -\> **New Template** and configure it with the following settings. This template is the blueprint for your fast-booting, reliable pods.

  * **Template Name:** `My Fast-Boot FLUX App` (or any name you prefer).
  * **Container Image:** `your_username/flux-app:latest` (use the name of the image you just pushed).
  * **Container Disk:** **50 GB** (a safe size for the OS and any temporary files).
  * **Environment Variables:**
      * Click **Add Variable**. In the dropdown, select the `HF_TOKEN` secret you just created.
      * Click **Add Variable** again. Set the Key to `HF_HOME` and the Value to `/workspace/.cache`.
      * Click **Add Variable** again. Set the Key to `TMPDIR` and the Value to `/workspace/tmp`.
  * **Container Start Command:** Paste this command. It will use your secret to log in non-interactively and then start the pod's essential services.
    ```bash
    bash -c 'huggingface-cli login --token $HF_TOKEN --add-to-git-credential=false && /start.sh'
    ```
  * **TCP Ports:** Add a port mapping for a stable SSH connection.
      * Set the **private container port** to `22`.

-----

## Phase 3: Deploy and Work

With the setup complete, deploying and working is now a fast and simple process.

### Step 6: Deploy Your Pod

1.  Go to the **GPU Cloud** to deploy a new pod.
2.  Select your desired GPU.
3.  Click **"Deploy from a Template"** and choose the `My Fast-Boot FLUX App` template you just created.
4.  Under storage options, attach your small **Network Volume** (e.g., 10 GB) to the `/workspace` mount path. This volume should contain your Python scripts (like `run_flux.py`) and your `.vscode` folder.
5.  Deploy the pod.

### Step 7: Connect and Run

Your new pod will now start in seconds. You can connect via VS Code using the provided SSH credentials.

Once connected, all Python libraries will be pre-installed, and your authentication will be handled automatically. You can immediately open a terminal and run your script:

```bash
python3 run_flux.py
```