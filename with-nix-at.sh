#!/usr/bin/env bash

set -eo pipefail

# the first argument should be a git revision
if [ -z "$1" ]; then
    echo "Usage: $0 <git-revision>"
    exit 1
fi

revspec="$1"

test -e with-nix-at.sh ||
  ( echo "Please run this script from the root of the repository" && exit 1 )

test -d lean4 || git clone --single-branch https://github.com/leanprover/lean4 lean4
cd lean4
rev=$(git rev-parse --short "$revspec")
parent=$(git rev-parse --short "$rev^")
git -c advice.detachedHead=false checkout "$parent"
git reset --hard
before=$(git rev-parse --short HEAD:stage0)
after=failed
if nix --substituters https://cache.nixos.org/ run .#update-stage0-commit
then
  after=$(git rev-parse --short HEAD:stage0)
fi
cd ..
echo "$rev,$parent,$before,$after" >> with-nix.log
