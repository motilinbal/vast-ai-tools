#!/bin/bash
# test_hypothesis.sh: A minimal script to test if capturing and re-parsing
# a multi-line string from a function output is causing the jq error.

# Exit on error and print each command, mirroring the real script's environment.
set -e
set -x

# 1. Mock function that replicates the SUCCESSFUL output of the real function.
# It simply prints a hardcoded, multi-line JSON string.
mock_get_details() {
  echo '{
  "host": "194.68.245.173",
  "port": 22049
}'
}

echo "--- TESTING HYPOTHESIS: Multi-line string handling ---"

# 2. Capture the multi-line output from the mock function into a variable.
# This is identical to the 'ssh_details=$(...)' step in the failing script.
echo "STEP A: Capturing output from mock function..."
details_string=$(mock_get_details)

# 3. Print the contents of the variable to verify its integrity.
# 'cat -A' will show invisible characters like trailing spaces or carriage returns ($).
echo "STEP B: Verifying captured string contents (viewing invisible chars)..."
echo "$details_string" | cat -A

# 4. Attempt to parse the captured string with jq.
# This is the exact operation that fails in the real script.
echo "STEP C: Piping the captured string into jq to extract '.host'..."
host=$(echo "$details_string" | jq -r '.host')

# 5. If the script reaches this point without error, the test has passed.
echo "--- HYPOTHESIS TEST SUCCEEDED ---"
echo "Successfully extracted host: ${host}"




        # set -x                                      # echo every command
        # echo "API_URL=[$API_URL]" >&2
        # echo "QUERY_PAYLOAD=[$query_payload]" >&2  # wrap in [] to spot hidden spaces/CRs
        # curl -v -X POST -H "Content-Type: application/json" \
        #     -d "$query_payload" "$API_URL" \
        #     -o /tmp/raw_response.json -w "\nHTTP_STATUS:%{http_code}\n" >&2
        # echo "--- RAW RESPONSE DUMP ---" >&2
        # cat -A /tmp/raw_response.json >&2          # show CRs (^M) and invisible chars
        # echo "--- END DUMP ---" >&2