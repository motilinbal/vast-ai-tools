# Stage 1: Base Image
FROM vastai/pytorch:cuda-12.4.1-auto

# Stage 2: System Dependencies & SSH Setup
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    # Generate the SSH host keys during the build.
    && ssh-keygen -A

# THE FINAL FIX: Create the sshd directory with correct permissions in the image itself.
RUN mkdir -p /var/run/sshd && chmod 0755 /var/run/sshd

# Copy the hardened sshd_config file into the image.
COPY hardened_sshd_config /etc/ssh/sshd_config
# Ensure correct, restrictive permissions on the configuration file
RUN chmod 600 /etc/ssh/sshd_config

# Stage 3: Python Dependencies
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 4: Final Configuration
EXPOSE 22 8080
CMD ["/bin/bash"]