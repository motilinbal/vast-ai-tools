import configparser
import os
from pathlib import Path
import subprocess
import sys
from typing import List, Dict, Optional, Tuple


def retrieve_ssh_details() -> str:
    """
    Parse SSH configs, collect hosts, prompt if multiple, return selected alias.
    
    This function reads the main SSH config file (~/.ssh/config) and any included
    config files (typically from ~/.ssh/config.d/) to extract all available host aliases.
    It then prompts the user to select a host if multiple are available.
    
    Returns:
        str: The selected host alias
        
    Raises:
        FileNotFoundError: If no SSH config file exists at ~/.ssh/config
        ValueError: If no SSH hosts are found in the config files
        KeyboardInterrupt: If the user cancels the host selection
    """
    config_dir = Path(os.path.expanduser("~/.ssh"))
    main_config = config_dir / "config"
    
    # Check if main SSH config exists
    if not main_config.exists():
        raise FileNotFoundError(f"No SSH config at {main_config}")
    
    # Find Include patterns by reading the file directly
    include_files = [main_config]
    try:
        with open(main_config, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('Include '):
                    include_pattern = line[8:].strip()  # Remove 'Include ' prefix
                    if '*' in include_pattern:
                        # Handle wildcard includes like 'config.d/*'
                        include_dir = config_dir / include_pattern.split('*')[0].strip('/')
                        if include_dir.exists() and include_dir.is_dir():
                            include_files.extend([f for f in include_dir.glob('*') if f.is_file()])
                    else:
                        # Handle direct includes
                        include_file = config_dir / include_pattern
                        if include_file.exists() and include_file.is_file():
                            include_files.append(include_file)
    except Exception as e:
        print(f"Warning: Error reading includes from {main_config}: {e}", file=sys.stderr)
    
    # Parse all files for Hosts
    all_hosts: List[str] = []
    for file_path in include_files:
        if not file_path.exists():
            continue
            
        try:
            with open(file_path, 'r') as f:
                current_hosts = []
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Handle Host declarations
                    if line.startswith('Host '):
                        # Extract host aliases from the line
                        host_aliases = line[5:].strip().split()
                        # Skip wildcard hosts
                        for alias in host_aliases:
                            if alias != '*' and alias not in all_hosts:
                                all_hosts.append(alias)
        except Exception as e:
            print(f"Warning: Error reading {file_path}: {e}", file=sys.stderr)
            continue
    
    if not all_hosts:
        raise ValueError("No SSH hosts found in configs")
    
    # If only one host, return it directly
    if len(all_hosts) == 1:
        return all_hosts[0]
    
    # Prompt user to select from multiple hosts
    print("Available SSH hosts:")
    for i, host in enumerate(all_hosts, 1):
        print(f"{i}. {host}")
    
    try:
        while True:
            try:
                choice = int(input("Select host number: "))
                if 1 <= choice <= len(all_hosts):
                    return all_hosts[choice - 1]
                print(f"Invalid choice. Please enter a number between 1 and {len(all_hosts)}.")
            except ValueError:
                print("Please enter a valid number.")
    except KeyboardInterrupt:
        print("\nHost selection cancelled.")
        raise


def upload_file(local_path: str, remote_path: str) -> None:
    """
    Upload a single file to the remote instance using rsync.
    
    This function transfers a single file from the local machine to the remote host
    using rsync over SSH. It validates that the local path exists and is a file
    before attempting the transfer.
    
    Args:
        local_path (str): Path to the local file to upload
        remote_path (str): Destination path on the remote host
        
    Raises:
        ValueError: If the local path doesn't exist or is not a file
        subprocess.CalledProcessError: If the rsync command fails
        FileNotFoundError: If SSH config is not found or no hosts are available
    """
    try:
        alias = retrieve_ssh_details()
    except (FileNotFoundError, ValueError, KeyboardInterrupt) as e:
        print(f"Error retrieving SSH details: {e}")
        raise
        
    local_file = Path(local_path)
    if not local_file.exists():
        raise ValueError(f"Local path does not exist: {local_path}")
    if not local_file.is_file():
        raise ValueError(f"Local path is not a file: {local_path}")
    
    # If remote_path is a directory, append the filename
    remote_file = remote_path
    if remote_path.endswith('/'):
        remote_file = remote_path + local_file.name
    
    # Construct and execute rsync command
    cmd = ["rsync", "-avz", "--progress", str(local_file), f"{alias}:{remote_file}"]
    try:
        print(f"Uploading {local_path} to {alias}:{remote_file}...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully uploaded {local_path} to {remote_file}")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        error_msg = f"Upload failed: {e.stderr if e.stderr else str(e)}"
        print(error_msg, file=sys.stderr)
        raise subprocess.CalledProcessError(e.returncode, e.cmd, error_msg)
    except Exception as e:
        print(f"Unexpected error during upload: {e}", file=sys.stderr)
        raise


def download_file(remote_path: str, local_path: str) -> None:
    """
    Download a single file from the remote instance using rsync.
    
    This function transfers a single file from the remote host to the local machine
    using rsync over SSH.
    
    Args:
        remote_path (str): Path to the remote file to download
        local_path (str): Destination path on the local machine
        
    Raises:
        subprocess.CalledProcessError: If the rsync command fails
        FileNotFoundError: If SSH config is not found or no hosts are available
    """
    try:
        alias = retrieve_ssh_details()
    except (FileNotFoundError, ValueError, KeyboardInterrupt) as e:
        print(f"Error retrieving SSH details: {e}")
        raise
    
    # Ensure local directory exists
    local_dir = Path(local_path).parent
    if not local_dir.exists():
        try:
            local_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {local_dir}")
        except Exception as e:
            print(f"Error creating directory {local_dir}: {e}", file=sys.stderr)
            raise
    
    # Construct and execute rsync command
    cmd = ["rsync", "-avz", "--progress", f"{alias}:{remote_path}", local_path]
    try:
        print(f"Downloading {alias}:{remote_path} to {local_path}...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully downloaded {remote_path} to {local_path}")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        error_msg = f"Download failed: {e.stderr if e.stderr else str(e)}"
        print(error_msg, file=sys.stderr)
        raise subprocess.CalledProcessError(e.returncode, e.cmd, error_msg)
    except Exception as e:
        print(f"Unexpected error during download: {e}", file=sys.stderr)
        raise


def upload_folder(local_dir: str, remote_dir: str) -> None:
    """
    Upload a folder recursively to the remote instance using rsync.
    
    This function transfers a folder and all its contents from the local machine
    to the remote host using rsync over SSH. The trailing slash is added to ensure
    content sync rather than creating a nested directory.
    
    Args:
        local_dir (str): Path to the local directory to upload
        remote_dir (str): Destination directory path on the remote host
        
    Raises:
        ValueError: If the local path doesn't exist or is not a directory
        subprocess.CalledProcessError: If the rsync command fails
        FileNotFoundError: If SSH config is not found or no hosts are available
    """
    try:
        alias = retrieve_ssh_details()
    except (FileNotFoundError, ValueError, KeyboardInterrupt) as e:
        print(f"Error retrieving SSH details: {e}")
        raise
        
    local_directory = Path(local_dir)
    if not local_directory.exists():
        raise ValueError(f"Local directory does not exist: {local_dir}")
    if not local_directory.is_dir():
        raise ValueError(f"Local path is not a directory: {local_dir}")
    
    # Append / for content sync (syncs contents of dir, not dir itself)
    local_source = str(local_directory) + '/'
    remote_target = remote_dir.rstrip('/') + '/'
    
    # Construct and execute rsync command
    cmd = ["rsync", "-avz", "--progress", local_source, f"{alias}:{remote_target}"]
    try:
        print(f"Uploading folder {local_dir} to {alias}:{remote_target}...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully uploaded folder {local_dir} to {remote_target}")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        error_msg = f"Upload failed: {e.stderr if e.stderr else str(e)}"
        print(error_msg, file=sys.stderr)
        raise subprocess.CalledProcessError(e.returncode, e.cmd, error_msg)
    except Exception as e:
        print(f"Unexpected error during folder upload: {e}", file=sys.stderr)
        raise


def download_folder(remote_dir: str, local_dir: str) -> None:
    """
    Download a folder recursively from the remote instance using rsync.
    
    This function transfers a folder and all its contents from the remote host
    to the local machine using rsync over SSH. The trailing slash is added to ensure
    content sync rather than creating a nested directory.
    
    Args:
        remote_dir (str): Path to the remote directory to download
        local_dir (str): Destination directory path on the local machine
        
    Raises:
        subprocess.CalledProcessError: If the rsync command fails
        FileNotFoundError: If SSH config is not found or no hosts are available
    """
    try:
        alias = retrieve_ssh_details()
    except (FileNotFoundError, ValueError, KeyboardInterrupt) as e:
        print(f"Error retrieving SSH details: {e}")
        raise
    
    # Ensure local directory exists
    local_directory = Path(local_dir)
    if not local_directory.exists():
        try:
            local_directory.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {local_directory}")
        except Exception as e:
            print(f"Error creating directory {local_directory}: {e}", file=sys.stderr)
            raise
    
    # Append / for content sync (syncs contents of dir, not dir itself)
    remote_source = remote_dir.rstrip('/') + '/'
    local_target = str(local_directory) + '/'
    
    # Construct and execute rsync command
    cmd = ["rsync", "-avz", "--progress", f"{alias}:{remote_source}", local_target]
    try:
        print(f"Downloading folder {alias}:{remote_source} to {local_target}...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully downloaded folder {remote_source} to {local_target}")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        error_msg = f"Download failed: {e.stderr if e.stderr else str(e)}"
        print(error_msg, file=sys.stderr)
        raise subprocess.CalledProcessError(e.returncode, e.cmd, error_msg)
    except Exception as e:
        print(f"Unexpected error during folder download: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    """
    Example usage of the file transfer functions.
    
    Uncomment the desired function calls to test file transfers.
    Make sure you have SSH keys set up and the remote host is configured
    in your ~/.ssh/config file.
    """
    try:
        # Test SSH host retrieval
        print("Testing SSH host retrieval...")
        host_alias = retrieve_ssh_details()
        print(f"Selected host: {host_alias}")
        
        # Example transfers (uncomment to use):
        # upload_file("local_file.txt", "/workspace/remote_file.txt")
        # download_file("/workspace/remote_file.txt", "local_file.txt")
        # upload_folder("local_dir", "/workspace/remote_dir")
        # download_folder("/workspace/remote_dir", "local_dir")
        
    except Exception as e:
        print(f"Error in example usage: {e}", file=sys.stderr)
        sys.exit(1)