# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --new-run-id)
      NEW_RUN_ID="$2"
      shift 2
      ;;
    --task-id)
      TASK_ID="$2"
      shift 2
      ;;
    --*)
      echo "Unknown option $1"
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

cd runs
mkdir -p ${NEW_RUN_ID}/${TASK_ID}
for old_run_id in $(ls -d github-action-*); do
  # if old_run_id/${TASK_ID} exists, then copy it to ${NEW_RUN_ID}/${TASK_ID}/
  # Exclude if old_run_id starts with "github-action-nop" or "github-action-oracle" because they are not real agents
  if [[ "${old_run_id}" != github-action-nop* ]] && [[ "${old_run_id}" != github-action-oracle* ]]; then
    if [ -d "${old_run_id}/${TASK_ID}" ]; then
      cp -r ${old_run_id}/${TASK_ID}/* ${NEW_RUN_ID}/${TASK_ID}/
    fi
  fi
done

# consolidate results.json
# $.results in ${old_run_id}/results.json is a list of results and has a single result object
# we need to consolidate the $.results for each task in ${new_run_id}/results.json
# Gather all results.json files for this task
results_files=()
for old_run_id in $(ls -d github-action-*); do
  # Exclude if old_run_id starts with "github-action-nop" or "github-action-oracle" because they are not real agents
  if [[ "${old_run_id}" != github-action-nop* ]] && [[ "${old_run_id}" != github-action-oracle* ]]; then
    if [ -f "${old_run_id}/results.json" ]; then
      results_files+=("${old_run_id}/results.json")
    fi
  fi
done

echo "Results files: ${results_files[@]}"

# Extract all result objects under .results[] and combine into a single array
jq -s '
  # $ is an array of results.json
  # For each, grab .results[] and collect into one big array, preserving any other outer fields from the first file
  def merged_results:
    map(.results) | flatten;
  if length > 0 then
    .[0] * {results: merged_results}
  else
    {}
  end
' "${results_files[@]}" > "${NEW_RUN_ID}/results.json"
