#!/usr/bin/env bash

set -eo pipefail

# the first argument should be a git revision
if [ -z "$1" ]; then
    echo "Usage: $0 <source-revision> [<stage0-tree>]"
    exit 1
fi

revspec="$1"
treespec="$2"

test -e with-nix.sh ||
  ( echo "Please run this script from the root of the repository" && exit 1 )

test -d lean4 || git clone --single-branch https://github.com/leanprover/lean4 lean4
cd lean4

rev=$(git rev-parse --short "$revspec")

git -c advice.detachedHead=false checkout -f "$rev"
git reset --hard

if [ -n "$treespec" ]
then
  git rm -rf --quiet stage0
  git read-tree --prefix stage0 "$treespec"
  git restore stage0
fi
before=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD
if [ -n "$treespec" ]
then
  git checkout HEAD -- stage0/src/stdlib_flags.h
  # we want update-stage0-commit not fail due to an empty commit
  git reset --soft 4f5cafdebfa02c041f4dcd8c2ebe3e463bf32343
fi

after=failed
if nix --substituters https://cache.nixos.org/ run .#update-stage0-commit
then
  after=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD
fi
cd ..
echo "$rev,$before,$after" >> with-nix.log
