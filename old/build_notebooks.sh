#!/usr/bin/env bash

# get parent folder
parent=$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd)")

# get folder with notebooks
dir=$1

# path
path="$parent/$dir"

echo $path
# FILES="$(find $path -type f -name '*.ipynb' -not -path '*_checkpoints*')"

# find nbs -type f -name '*.ipynb' -not -path '*_checkpoints*' -print0 | gxargs -0 -I {} -P 4 nbdev_build_lib --fname "{}"
find nbs -type f -name '*.ipynb' -not -path '*_checkpoints*' -not -path 'index.ipynb' -print0 | gxargs -0 -I {} -P 2 nbdev_build_lib --fname "{}"

# for f in $FILES
# do
#     echo "$f"
#     nbdev_build_lib --fname "$f"
# done
