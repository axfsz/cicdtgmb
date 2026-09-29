#!/usr/bin/env bash
set -euo pipefail

source .env

JOB_NAME="${1:-activity-rpc-testa}"
JOB_TOKEN="${JOB_NAME}-token"
COOKIE_FILE="/tmp/jenkins-cookie-${JOB_NAME}.txt"
CRUMB_FILE="/tmp/jenkins-crumb-${JOB_NAME}.json"

curl -sS -u "${JENKINS_USER}:${JENKINS_API_TOKEN}" \
  -c "${COOKIE_FILE}" \
  "${JENKINS_URL}/crumbIssuer/api/json" > "${CRUMB_FILE}"

CRUMB_FIELD=$(jq -r '.crumbRequestField' "${CRUMB_FILE}")
CRUMB_VALUE=$(jq -r '.crumb' "${CRUMB_FILE}")

curl -i -X POST \
  -u "${JENKINS_USER}:${JENKINS_API_TOKEN}" \
  -b "${COOKIE_FILE}" \
  -H "${CRUMB_FIELD}: ${CRUMB_VALUE}" \
  "${JENKINS_URL}/job/${JOB_NAME}/buildWithParameters?token=${JOB_TOKEN}" \
  --data-urlencode "BRANCH_NAME=${DEFAULT_BRANCH:-main}" \
  --data-urlencode "K8S_NAMESPACE=${DEFAULT_NAMESPACE:-testa}" \
  --data-urlencode "PUSH_LATEST=${DEFAULT_PUSH_LATEST:-true}" \
  --data-urlencode "RUN_GO_TEST=${DEFAULT_RUN_GO_TEST:-false}"
