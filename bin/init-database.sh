#!/usr/bin/env bash
# Script: Database Initialization
# Purpose: Create tables and seed the Postgres database by invoking the deployed backend Lambda
# Usage: ./init-database.sh [aws|local] [--no-sample-data]
# Default: aws

set -e

# Usage helper
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: $0 [aws|local] [--no-sample-data]"
    echo "Create missing tables and seed test users + sample data in the deployed database"
    echo ""
    echo "Arguments:"
    echo "  aws               Initialize the AWS RDS database (default)"
    echo "  local             Initialize the LocalStack-deployed backend's database"
    echo ""
    echo "Options:"
    echo "  --no-sample-data  Only create tables and test users"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Environment:"
    echo "  BACKEND_NAME      Backend folder whose Lambda runs the init (default: v1)"
    echo "  SEED_PASSWORD     Password for the seeded test/sample accounts in AWS. If unset, a random"
    echo "                    one is generated and printed once (locally they always use password123)"
    echo ""
    echo "Notes:"
    echo "  - Safe to run repeatedly: existing tables and data are left untouched"
    echo "  - Runs inside the Lambda because RDS is only reachable from within the VPC"
    echo "  - Requires a prior ./bin/deploy-backend.sh run (reads terraform outputs)"
    exit 0
fi

echo "======================================="
echo "Coding Workshop - Database Initialization"
echo "======================================="
echo ""

# Set up PATH and AWS region
export PATH="$HOME/.local/bin:$PATH"
export AWS_REGION=${AWS_REGION:-us-east-1}

# Verify required dependencies
terraform --version > /dev/null 2>&1 || { echo "ERROR: 'terraform' is missing. Aborting..."; exit 1; }
aws --version > /dev/null 2>&1 || { echo "ERROR: 'aws' is missing. Aborting..."; exit 1; }
jq --version > /dev/null 2>&1 || { echo "ERROR: 'jq' is missing. Aborting..."; exit 1; }

# Resolve script directory and project root paths
SCRIPT_DIR="$(cd "$(dirname "$0")" > /dev/null 2>&1 || exit 1; pwd -P)"
PROJECT_ROOT="$(cd $SCRIPT_DIR/.. > /dev/null 2>&1 || exit 1; pwd -P)"

# Define configuration file paths
ENVIRONMENT_CONFIG="$PROJECT_ROOT/ENVIRONMENT.config"
INFRA_DIR="$PROJECT_ROOT/infra"
ENVIRONMENT="aws"
SAMPLE_DATA=true
BACKEND_NAME=${BACKEND_NAME:-v1}

for arg in "$@"; do
    case "$arg" in
        aws|local) ENVIRONMENT="$arg" ;;
        --no-sample-data) SAMPLE_DATA=false ;;
        *) echo "ERROR: Unknown argument '$arg'. See --help."; exit 1 ;;
    esac
done

echo "INFO: Environment - $ENVIRONMENT"

if [ "$ENVIRONMENT" = "aws" ]; then
    # Load participant-specific configuration (credentials) if available
    if [ -f "$ENVIRONMENT_CONFIG" ]; then
        source $ENVIRONMENT_CONFIG
    else
        echo "WARN: $ENVIRONMENT_CONFIG is missing"
    fi
else
    # Local development configuration — override credentials for LocalStack
    export AWS_ENDPOINT_URL="http://localhost.localstack.cloud:4566"
    export AWS_ACCESS_KEY_ID=test
    export AWS_SECRET_ACCESS_KEY=test
    export AWS_REGION=us-east-1
    unset AWS_SESSION_TOKEN
fi

# Look up the deployed Lambda name (e.g. coding-workshop-v1-<app id>) from terraform outputs
cd "$INFRA_DIR"
FUNCTION_NAME=$(terraform output -json lambda_urls 2>/dev/null \
    | jq -r --arg name "$BACKEND_NAME" 'keys[] | select(contains("-" + $name + "-"))' | head -n 1)
if [ -z "$FUNCTION_NAME" ]; then
    echo "ERROR: No deployed Lambda found for backend '$BACKEND_NAME'. Run ./bin/deploy-backend.sh first."
    exit 1
fi

echo "INFO: Invoking $FUNCTION_NAME (sample data: $SAMPLE_DATA)..."
RESPONSE_FILE=$(mktemp)
trap 'rm -f "$RESPONSE_FILE"' EXIT

# Lambda timeout is 300s; a paused Aurora Serverless cluster can take a few seconds to resume
# jq builds the payload so a SEED_PASSWORD containing quotes etc. is escaped correctly
PAYLOAD=$(jq -cn --argjson sample "$SAMPLE_DATA" --arg pw "${SEED_PASSWORD:-}" \
    '{action: "init_db", sample_data: $sample} + (if $pw != "" then {seed_password: $pw} else {} end)')
INVOKE_RESULT=$(aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --cli-binary-format raw-in-base64-out \
    --cli-read-timeout 310 \
    --log-type Tail \
    --payload "$PAYLOAD" \
    "$RESPONSE_FILE")

# Show the tail of the Lambda's logs (seed script output, or the traceback on failure)
echo "$INVOKE_RESULT" | jq -r '.LogResult // empty' | base64 --decode 2>/dev/null | grep -v '^\(START\|END\|REPORT\) ' || true

if [ -n "$(echo "$INVOKE_RESULT" | jq -r '.FunctionError // empty')" ]; then
    echo "ERROR: Database initialization failed:"
    cat "$RESPONSE_FILE"; echo ""
    exit 1
fi

# a generated seed password is only ever returned here (it isn't logged), so show it clearly once
SEED_RESULT=$(jq -r '.seed_password // empty' "$RESPONSE_FILE")
echo "INFO: Database initialization complete! $(jq -c 'del(.seed_password)' "$RESPONSE_FILE")"
if [ -n "$SEED_RESULT" ]; then
    echo ""
    echo "IMPORTANT: seeded accounts (admin, engineer, employee, ...) now use this password:"
    echo "    $SEED_RESULT"
    echo "Save it now: it is not stored anywhere. Set SEED_PASSWORD to choose your own next time."
fi
