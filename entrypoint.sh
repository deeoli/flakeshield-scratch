#!/bin/sh
set -e

# Pass all arguments directly to flakeshield CLI
exec flakeshield "$@"

# build command
cmd=("flakeshield" "--reports" "$reports" "--out" "$out" "--db" "$db")
if [ "$enable_semantic" = "true" ]; then
  cmd+=("--enable-semantic")
fi
if [ "$warn_on_high" = "true" ]; then
  cmd+=("--warn-on-high")
fi
if [ "$fail_on_critical" = "true" ]; then
  cmd+=("--fail-on-critical")
fi
if [ -n "$max_risk_threshold" ]; then
  cmd+=("--max-risk-threshold" "$max_risk_threshold")
fi

"${cmd[@]}"

# generate PR summary and comment when running in PR context
if [ "$GITHUB_EVENT_NAME" = "pull_request" ]; then
  # create summary file
  flakeshield pr-summary --json "${out}.json" --out outputs/pr_comment.md || true
  # attempt comment if token available
  if [ -n "$GITHUB_TOKEN" ]; then
    repo="$GITHUB_REPOSITORY"
    owner=${repo%%/*}
    repo_name=${repo#*/}
    issue_number=$(jq --raw-output .number < "$GITHUB_EVENT_PATH")
    body=$(sed 's/"/\\"/g' outputs/pr_comment.md)
    marker="<!-- flakeshield-report -->"
    # fetch existing comments
    comments=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
      "https://api.github.com/repos/$repo/issues/$issue_number/comments")
    existing=$(echo "$comments" | jq -r '.[] | select(.body|contains("'"$marker"'")) | .id' | head -n1)
    if [ -n "$existing" ]; then
      curl -s -X PATCH -H "Authorization: token $GITHUB_TOKEN" \
           -d "{\"body\": \"$marker\\n$body\"}" \
           "https://api.github.com/repos/$repo/issues/comments/$existing" || true
    else
      curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
           -d "{\"body\": \"$marker\\n$body\"}" \
           "https://api.github.com/repos/$repo/issues/$issue_number/comments" || true
    fi
  fi
fi
