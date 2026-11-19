#!/usr/bin/env bash
# One teacher GPU + one simulation GPU, currently only the scheduler's v100 pool.
set -euo pipefail
cd /home/yeliheng/VLM_Grasp_Interactive
if [[ $# -lt 1 ]]; then
    echo 'Usage: bash training/server/run_pilot.sh OUTPUT_DIRECTORY [SEED_COUNT=2] [START_SEED=1000]'
    exit 2
fi
RUN_OUTPUT="$1"
RUN_SEEDS="${2:-2}"
RUN_START="${3:-1000}"
if squeue -h -u yeliheng -o '%j' | grep -qx 'grasp-teacher'; then
    echo 'A teacher job is already running or pending. Inspect status.py first.'
    exit 1
fi
if /home/yeliheng/grasp_server/env_sim/bin/python -c 'import urllib.request; print(urllib.request.build_opener(urllib.request.ProxyHandler({})).open("http://127.0.0.1:18765/health",timeout=3).status)' >/dev/null 2>&1; then
    echo 'Teacher already running. Check status.py before submitting overlapping collections.'
    exit 1
fi
TEACHER_JOB=''
PREFLIGHT_JOB=''
cleanup_submission() {
    [[ -z "$TEACHER_JOB" ]] || scancel "$TEACHER_JOB" || true
    [[ -z "$PREFLIGHT_JOB" ]] || scancel "$PREFLIGHT_JOB" || true
}
trap cleanup_submission ERR
TEACHER_JOB=$(sbatch --parsable training/server/teacher.slurm)
PREFLIGHT_JOB=$(sbatch --parsable training/server/preflight.slurm)
# Run even after a failed preflight so the collector can clean up this teacher.
# Its wrapper validates the exact preflight job id before loading the simulation.
COLLECT_JOB=$(sbatch --parsable --dependency="afterany:$PREFLIGHT_JOB" \
 --export="ALL,GRASP_TEACHER_JOB=$TEACHER_JOB,GRASP_PREFLIGHT_JOB=$PREFLIGHT_JOB" training/server/collect.slurm \
 --output "$RUN_OUTPUT" --seeds "$RUN_SEEDS" --start-seed "$RUN_START")
/home/yeliheng/grasp_server/env_sim/bin/python -c \
 'import json,sys;from pathlib import Path; p=Path("/home/yeliheng/grasp_server"); d={"output":str(Path(sys.argv[1]).resolve()),"job_id":sys.argv[2],"teacher_job":sys.argv[3],"preflight_job":sys.argv[4]}; (p/"latest_collection.json").write_text(json.dumps(d,indent=2)); print(json.dumps(d,indent=2))' \
 "$RUN_OUTPUT" "$COLLECT_JOB" "$TEACHER_JOB" "$PREFLIGHT_JOB"
trap - ERR
