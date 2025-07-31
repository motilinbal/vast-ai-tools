# Start from the official RunPod PyTorch image
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Install all Python dependencies directly into the image
RUN pip install diffusers transformers accelerate sentencepiece protobuf torch --upgrade

# Set the default command to run when the container starts
CMD ["/start.sh"]