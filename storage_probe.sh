#!/bin/bash
source /util/opt/lmod/lmod/init/profile
module use /util/opt/hcc-modules/Common
module load anaconda
source activate dashing
cd /util/admin/dashing-storage
python /util/admin/dashing-storage/storage_probe.py
conda deactivate
module unload anaconda

