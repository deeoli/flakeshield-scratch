#!/bin/sh
set -e

reports="$1"
out="$2"
db="$3"
enable_semantic="$4"
warn_on_high="$5"
fail_on_critical="$6"
max_risk_threshold="$7"

set -- --reports "$reports" --out "$out" --db "$db"

if [ "$enable_semantic" = "true" ]; then
  set -- "$@" --enable-semantic
fi

if [ "$warn_on_high" = "true" ]; then
  set -- "$@" --warn-on-high
fi

if [ "$fail_on_critical" = "true" ]; then
  set -- "$@" --fail-on-critical
fi

if [ -n "$max_risk_threshold" ]; then
  set -- "$@" --max-risk-threshold "$max_risk_threshold"
fi

exec flakeshield "$@"