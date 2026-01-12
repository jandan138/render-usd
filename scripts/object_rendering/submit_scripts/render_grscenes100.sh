bash -i -c "
if [ \$# -ne 2 ]; then
    echo \"Usage: \$0 chunk_id chunk_total\"
    exit 1
fi

chunk_id=\$1
chunk_total=\$2

cd /cpfs/user/caopeizhou/projects/GRGenerator/object_extraction_and_caption && \\
source /cpfs/user/caopeizhou/.bashrc && \\
source activate omniscenes && \\
export OMNI_KIT_ACCEPT_EULA=YES && \\
export PYTHONUNBUFFERED=1 && \\

python object_rendering.py \\
    --chunk_id \$chunk_id \\
    --chunk_total \$chunk_total


" "$0" "$@"