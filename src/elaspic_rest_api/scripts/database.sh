#!/bin/bash
# #SBATCH --time=24:00:00
# #SBATCH --nodes=1
# #SBATCH --ntasks-per-node=1
# #SBATCH --mem=0
#SBATCH --partition kimprod
#SBATCH --job-name=elaspic-database
#SBATCH --export=ALL
#SBATCH --mail-type=BEGIN
#SBATCH --mail-user=alexey.strokach@kimlab.org
#SBATCH --output=/home/kimlab1/jobsubmitter/pbs-output/elaspic-database-%N-%j.out
#SBATCH --error=/home/kimlab1/jobsubmitter/pbs-output/elaspic-database-%N-%j.err
set -ex

function finish {
  echo "Moving lock file to the finished folder..."
  mv -f "${lock_filename}" "${lock_filename_finished}"
}
trap finish INT TERM EXIT

cd "/home/kimlab1/database_data/elaspic_v2"
mkdir -p "./pbs-output"
exec >"./pbs-output/${SLURM_JOB_ID}.out" 2>"./pbs-output/${SLURM_JOB_ID}.err"

echo `hostname`
# source activate elaspic
export PATH="/home/kimlab1/jobsubmitter/anaconda3/envs/elaspic$([[ -z ${ELASPIC_VERSION} ]] || echo "-${ELASPIC_VERSION}")/bin:$PATH"
elaspic run \
    --pdb_dir='/home/kimlab1/database_data/pdb/ftp/data/structures/divided/pdb/' \
    --blast_db_dir='/home/kimlab1/database_data/blast/db' \
    --archive_dir='/home/kimlab1/database_data/elaspic_v2/' \
    --connection_string="mysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/elaspic" \
    -u "${protein_id}" -m "${mutations}" -t ${elaspic_run_type}

echo "Finished successfully!"

exit 0
