#!/usr/bin/env bash

set -eo pipefail

# the first argument should be a git revision
if [ -z "$1" ]; then
    echo "Usage: $0 <git-revision>"
    exit 1
fi

revspec="$1"

mkdir -p stage0

test -e with-nix-at.sh ||
  ( echo "Please run this script from the root of the repository" && exit 1 )

test -d lean4 || git clone --single-branch https://github.com/leanprover/lean4 lean4
cd lean4
rev=$(git rev-parse --short "$revspec")
git -c advice.detachedHead=false checkout "$rev"
git reset --hard
before=$(git rev-parse --short HEAD:stage0)
nix run .#update-stage0-commit
after=$(git rev-parse --short HEAD:stage0)
cd ..

if ! test -d stage0/"$after"; then
    mv lean4/stage0 stage0/"$after"/
fi
echo "$0 $@" > "stage0/$after-from-$before.sh"
# git add stage0/$rev/

echo "Built $after from $before"