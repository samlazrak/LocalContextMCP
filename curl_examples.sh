#!/bin/bash
# Example curl commands for MCP server JSON-RPC endpoints
URL="http://localhost:8080/"

run_and_capture() {
  desc="$1"
  shift
  echo "==== $desc ===="
  output=$(eval "$@")
  echo "$output"
  echo
}

# tools/list
run_and_capture "tools/list" \
  "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/list\",\"id\":1}' | jq"

# tools/call (time)
run_and_capture "tools/call (time)" \
  "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"tool\":\"time\"},\"id\":2}' | jq"

# tools/call (git status)
run_and_capture "tools/call (git status)" \
  "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"tool\":\"git\",\"params\":{\"command\":\"status\"}},\"id\":3}' | jq"

# tools/call (web-search)
run_and_capture "tools/call (web-search)" \
  "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"tool\":\"web-search\",\"params\":{\"query\":\"openai\"}},\"id\":4}' | jq"

# resources/list
run_and_capture "resources/list" \
  "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"resources/list\",\"id\":5}' | jq"

# prompts/list
run_and_capture "prompts/list" \
  "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"prompts/list\",\"id\":6}' | jq"

# prompts/get (greet)
run_and_capture "prompts/get (greet)" \
  "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"prompts/get\",\"params\":{\"prompt\":\"greet\"},\"id\":7}' | jq"

# Add more as needed