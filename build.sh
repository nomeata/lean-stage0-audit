#!/usr/bin/env bash

set -eo pipefail

# the first argument should be a git revision
if [ -z "$1" ]; then
    echo "Usage: $0 <source-revision> [<stage0-tree>]"
    exit 1
fi

revspec="$1"
treespec="$2"

test -e build.sh ||
  ( echo "Please run this script from the root of the repository" && exit 1 )

test -d lean4 || git clone --single-branch https://github.com/leanprover/lean4 lean4
cd lean4

rev=$(git rev-parse --short "$revspec")

git -c advice.detachedHead=false checkout -f "$rev"
git reset --hard

if [ -z "$treespec" ]
then
  treespec=$(git rev-parse --short $(git write-tree --prefix=stage0))
fi    

git rm -rf --quiet stage0
git read-tree --prefix stage0 "$treespec"
git restore stage0
before=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD

if [ "$(git diff --name-only $rev^..$rev -- stage0)" = "stage0/src/stdlib_flags.h" ]
then
  # just a flag update, do not build anything, just apply this to the given tree
  git checkout "$rev" -- stage0/src/stdlib_flags.h
  after=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD
elif [ "$(git diff --name-only $rev^..$rev -- stage0)" = "stage0/src/lean.mk.in" ]
then
  # just a make file update, do not build anything, just apply this to the given tree
  git checkout "$rev" -- stage0/src/lean.mk.in
  after=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD
else
  git checkout HEAD -- stage0/src/lean.mk.in
  # we want update-stage0-commit not fail due to an empty commit
  git reset --soft 4f5cafdebfa02c041f4dcd8c2ebe3e463bf32343

  after=failed
  if nix --substituters https://cache.nixos.org/ run .#update-stage0-commit
  then
    after=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD

    # store stage0 in lean-stage0-audit repo, in case it is a stage0 that is not available
    # upstream
    git push .. $after:refs/stage0/$after
  fi
fi
cd ..
echo "$rev,$before,$after" >> builds.csv
