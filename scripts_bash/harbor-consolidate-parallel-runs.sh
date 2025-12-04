# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --new-job-id)
      NEW_JOB_ID="$2"
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

cd jobs
mkdir ${NEW_JOB_ID}
for old_job_id in $(ls -d github-action-*); do
  # if old_run_id/${TASK_ID} exists, then copy it to ${NEW_RUN_ID}/${TASK_ID}/
  # Exclude if old_run_id starts with "github-action-nop" or "github-action-oracle" because they are not real agents
  if [[ "${old_job_id}" != github-action-nop* ]] && [[ "${old_job_id}" != github-action-oracle* ]]; then
    # Match directories like ${TASK_ID} or ${TASK_ID}__xxxx (with random suffix)
    for task_dir in "${old_job_id}/${TASK_ID}"*; do
      if [ -d "${task_dir}" ]; then
        echo "Copying ${task_dir} to ${NEW_JOB_ID}"
        cp -r "${task_dir}" "${NEW_JOB_ID}/"
      fi
    done
  fi
done
