#!/usr/bin/env bash

set -e -o pipefail
shopt -s globstar

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

echo -n "Revision: "
git rev-parse --short "$revspec"
rev=$(git rev-parse --short "$revspec")

git reset --hard "$rev"
git clean -f

if [ -z "$treespec" ]
then
  treespec=$(git rev-parse --short $(git write-tree --prefix=stage0))
fi

echo -n "Tree: "
git rev-parse --short "$treespec^{tree}"

git rm -rf --quiet stage0
git read-tree --prefix stage0 "$treespec"
git restore stage0
before=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD

if [ "$(git diff --name-only $rev^..$rev -- stage0)" = "stage0/src/stdlib_flags.h" ]
then
  # just a flag update, do not build anything, just apply this to the given tree
  git checkout "$rev" -- stage0/src/stdlib_flags.h
  after=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD
elif [ "$(git diff --name-only $rev^..$rev -- stage0)" = "stage0/src/library/compiler/ir_interpreter.cpp" ]
then
  # like above, just more blunt (for https://github.com/leanprover/lean4/commit/79107a2316)
  git checkout "$rev" -- stage0/src/library/compiler/ir_interpreter.cpp
  after=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD
elif [ "$(git diff --name-only $rev^..$rev -- stage0)" = "stage0/src/lean.mk.in" ]
then
  # just a make file update, do not build anything, just apply this to the given tree
  git checkout "$rev" -- stage0/src/lean.mk.in
  after=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD
else
  git checkout HEAD -- stage0/src/lean.mk.in

  # some cherry-picking later build fixes
  if git merge-base --is-ancestor 802922ddaf40423f6d4e4aa8fea56f2439d0e448 HEAD &&
     git merge-base --is-ancestor HEAD ff097e952f7cee75608d4097c3e825a1f650ffe7^
  then
    echo "Applying parts of ff097e952f7cee75608d4097c3e825a1f650ffe7"
    git show ff097e952f7cee75608d4097c3e825a1f650ffe7 -- src/Init.lean|git apply -
  fi

  if git merge-base --is-ancestor 137c70f055e6d73f2a074b28faab7373a6fa4710 HEAD &&
     git merge-base --is-ancestor HEAD ff097e952f7cee75608d4097c3e825a1f650ffe7^
  then
    echo "Applying parts of ff097e952f7cee75608d4097c3e825a1f650ffe7"
    git show ff097e952f7cee75608d4097c3e825a1f650ffe7 -- src/Lean/Meta/Tactic/LinearArith/Nat.lean|git apply -
  fi

  if git merge-base --is-ancestor f7f04483b17a8459f1a7ef5ab7fa5bd5096b7660 HEAD &&
     git merge-base --is-ancestor HEAD 3f636b9f836c86958eb85280314500cdf5e69b32^
  then
    echo "Applying parts of 3f636b9f836c86958eb85280314500cdf5e69b32"
    git show 3f636b9f836c86958eb85280314500cdf5e69b32 -- src/Lean/Meta/Tactic/LinearArith.lean|git apply -
  fi

  if git merge-base --is-ancestor 0649e5fa8ac706d864a47c90dd2e643353eb9579 HEAD &&
     git merge-base --is-ancestor HEAD 4b03666eccad726d459cdb9dd6034f0089f60aaa^
  then
    echo "Applying 4b03666eccad726d459cdb9dd6034f0089f60aaa"
    git show 4b03666eccad726d459cdb9dd6034f0089f60aaa|git apply -
  fi

  git add .


  # we want update-stage0-commit not fail due to an empty commit
  git reset --soft 4f5cafdebfa02c041f4dcd8c2ebe3e463bf32343

  # some devs use #exit during bootstrapping, and maybe it does't fail the make
  # based update stage0, but it fails the nix one, so let's remove this
  sed -i -n '/^#exit/q;p' src/**/*.lean

  after=failed
  if nix --substituters https://cache.nixos.org/ run .#update-stage0-commit
  then
    after=$(git rev-parse --short $(git write-tree --prefix=stage0)) # use tree, not HEAD

  fi
fi


if [ "$after" != "failed" ]
then
    # store stage0 in lean-stage0-audit repo, in case it is a stage0 that is not available
    # upstream
    git push .. "$after:refs/stage0/$after"
fi

cd ..
echo "$rev,$before,$after,$LOGURL" >> builds.csv
