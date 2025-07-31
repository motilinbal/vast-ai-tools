import os
import vastai_sdk

# --- CONFIG ---
INSTANCE_ID_TO_DEBUG = 24380924
VASTAI_API_KEY = os.getenv("VASTAI_API_KEY")
# --- END CONFIG ---

if not VASTAI_API_KEY:
    print("Error: VASTAI_API_KEY environment variable not set.")
else:
    client = vastai_sdk.VastAI(api_key=VASTAI_API_KEY)
    
    # The 'logs' command will return the full stdout of the container startup process
    print(f"--- Fetching logs for instance {INSTANCE_ID_TO_DEBUG} ---")
    try:
        log_output = client.logs(INSTANCE_ID=INSTANCE_ID_TO_DEBUG)
        
        # Check if our detailed log was created and print it
        if "/root/onstart.log" in log_output:
            print(log_output)
        else:
            # If our log wasn't created, the container failed very early.
            # Print the raw logs from Vast.ai.
            print("Could not find /root/onstart.log. The container may have failed before the script could run.")
            print("Raw Vast.ai logs:")
            print(log_output)
            
    except Exception as e:
        print(f"An error occurred while fetching logs: {e}")
