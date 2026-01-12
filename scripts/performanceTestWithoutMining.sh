#!/usr/bin/env bash
set -euo pipefail

NS="${NS:-blockchain-microservices}"
URL="${URL:-http://localhost:5003/request/1}"
SLEEP="${SLEEP:-0.5}"
OUT_DIR="${OUT_DIR:-./hpa_test_out}"
mkdir -p "$OUT_DIR"

TIMES_FILE="$(mktemp "$OUT_DIR/times.XXXXXX")"
EVENT_LOG="$OUT_DIR/events.log"
CSV="$OUT_DIR/segments.csv"

echo "Event Time (UTC),Event Type,Requests Count,Avg Response (s),P95 Response (s),Min Response (s),Max Response (s),Total Pods,Master Pods,Requester Pods,Provider Pods,JWT Pods,Node Count" > "$CSV"

# ---- last observed counts (init to -1 so first refresh sets them) ----
LAST_TOTAL_PODS=-1
LAST_MASTER_PODS=-1
LAST_REQUESTER_PODS=-1
LAST_PROVIDER_PODS=-1
LAST_JWT_PODS=-1
LAST_NODE_COUNT=-1

# ---- helpers ----
refresh_counts() {
  CUR_TOTAL_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | wc -l | tr -d ' ')
  CUR_MASTER_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep -c "master-deployment" || true)
  CUR_REQUESTER_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep -c "requester-deployment" || true)
  CUR_PROVIDER_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep -c "provider-deployment" || true)
  CUR_JWT_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep -c "jwt-issuer-deployment" || true)
  CUR_NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ')
}

counts_changed() {
  [[ $CUR_TOTAL_PODS     -ne $LAST_TOTAL_PODS     ]] || \
  [[ $CUR_MASTER_PODS    -ne $LAST_MASTER_PODS    ]] || \
  [[ $CUR_REQUESTER_PODS -ne $LAST_REQUESTER_PODS ]] || \
  [[ $CUR_PROVIDER_PODS  -ne $LAST_PROVIDER_PODS  ]] || \
  [[ $CUR_JWT_PODS       -ne $LAST_JWT_PODS       ]] || \
  [[ $CUR_NODE_COUNT     -ne $LAST_NODE_COUNT     ]]
}

update_last_counts() {
  LAST_TOTAL_PODS=$CUR_TOTAL_PODS
  LAST_MASTER_PODS=$CUR_MASTER_PODS
  LAST_REQUESTER_PODS=$CUR_REQUESTER_PODS
  LAST_PROVIDER_PODS=$CUR_PROVIDER_PODS
  LAST_JWT_PODS=$CUR_JWT_PODS
  LAST_NODE_COUNT=$CUR_NODE_COUNT
}

summarize() {
  local label="${1:-Segment}"
  local when
  when="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

  local count avg p95 min max
  count=$(wc -l < "$TIMES_FILE" | tr -d ' ')
  # skip empty segments
  if [[ "${count:-0}" -le 0 ]]; then
    return 0
  fi

  avg=$(awk '{s+=$1} END {if(NR>0) printf "%.4f", s/NR; else print "0"}' "$TIMES_FILE")
  min=$(awk 'NR==1{m=$1} $1<m{m=$1} END{printf "%.4f", (NR?m:0)}' "$TIMES_FILE")
  max=$(awk 'NR==1{m=$1} $1>m{m=$1} END{printf "%.4f", (NR?m:0)}' "$TIMES_FILE")
  p95=$(sort -n "$TIMES_FILE" | awk -v n="$count" '
    BEGIN { idx = int(0.95*n); if (idx < 1) idx = 1; if (idx > n) idx = n }
    NR == idx { printf "%.4f", $1; exit }
    END { if (n==0) printf "0" }
  ')

  # use CURRENT counts we just computed
  echo "$when,$label,$count,$avg,$p95,$min,$max,$CUR_TOTAL_PODS,$CUR_MASTER_PODS,$CUR_REQUESTER_PODS,$CUR_PROVIDER_PODS,$CUR_JWT_PODS,$CUR_NODE_COUNT" | tee -a "$CSV"
}

reset_times() { : > "$TIMES_FILE"; }

on_exit() {
  echo
  refresh_counts
  summarize "Final Summary"
  echo "Wrote CSV: $CSV"
  echo "Events log: $EVENT_LOG"
  kill "$WP" "$WH" "$WN" 2>/dev/null || true
  exit 0
}
trap on_exit INT TERM

# ---- gate snapshots: only when counts actually changed ----
on_possible_event() {
  local source="${1:-K8s Change}"
  refresh_counts
  if counts_changed; then
    summarize "$source"
    reset_times
    update_last_counts
  fi
}

# ---- watchers ----
watch_pods() {
  kubectl get pods -n "$NS" -w --no-headers | \
  while IFS= read -r line; do
    echo "$(date +'%H:%M:%S') PODS $line" | tee -a "$EVENT_LOG" >/dev/null
    on_possible_event "Pods Changed"
  done
}
watch_hpa() {
  kubectl get hpa -n "$NS" -w --no-headers 2>/dev/null | \
  while IFS= read -r line; do
    echo "$(date +'%H:%M:%S') HPA  $line" | tee -a "$EVENT_LOG" >/dev/null
    on_possible_event "HPA Update"
  done
}
watch_nodes() {
  kubectl get nodes -w --no-headers | \
  while IFS= read -r line; do
    echo "$(date +'%H:%M:%S') NODE $line" | tee -a "$EVENT_LOG" >/dev/null
    on_possible_event "Node Changed"
  done
}

# ---- init baseline counts once ----
refresh_counts
update_last_counts

# ---- start watchers ----
watch_pods  & WP=$!
watch_hpa   & WH=$!
watch_nodes & WN=$!

echo "Sending requests to $URL (sleep ${SLEEP}s). Ctrl-C to stop."
while true; do
  t=$(curl -w "%{time_total}\n" -s "$URL" -o /dev/null || echo "")
  if [[ -n "$t" ]]; then
    printf "%s Request -> time: %ss\n" "$(date '+%H:%M:%S.%3N' 2>/dev/null || date '+%H:%M:%S')" "$t"
    echo "$t" >> "$TIMES_FILE"
  else
    printf "%s Request failed\n" "$(date '+%H:%M:%S.%3N' 2>/dev/null || date '+%H:%M:%S')"
  fi
  sleep "$SLEEP"
done