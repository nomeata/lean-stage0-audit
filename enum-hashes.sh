#!/usr/bin/env bash

git -C lean4 log --pretty='tformat:%h' --first-parent --topo-order master -- stage0 |
while read -r rev ; do
    tree=$(git -C lean4 rev-parse --short "$rev":stage0)
    echo "$rev,$tree"
done