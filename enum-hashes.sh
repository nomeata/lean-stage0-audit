#!/usr/bin/env bash

# builds the repo-digest.csv file

git -C lean4 log --pretty='tformat:%h' --first-parent --topo-order master -- stage0 |
while read -r rev ; do
    tree=$(git -C lean4 rev-parse --short "$rev":stage0)
    before_flags=""
    clean=true

    if [ "$(git -C lean4 diff --name-only "$rev^..$rev" stage0)" = "stage0/src/stdlib_flags.h" ]
    then
        before_flags=$(git -C lean4 rev-parse --short "$rev^":stage0)
    elif [ -n "$(git -C lean4 diff --name-only "$rev^..$rev" | grep -v ^stage0)" ]
    then
        clean=false
    fi
    echo "$rev,$tree,$before_flags,$clean"
done
