#!/usr/bin/env python3

import subprocess
import csv

bad_squashes = dict(csv.reader(open('bad-squashes.csv', 'r')))

def git(command):
    return subprocess.check_output(command, shell=True).decode().strip()

def git_log(arg):
    return git(f"git -C lean4 log --pretty='tformat:%h' --first-parent --topo-order " + arg).split("\n")

def get_tree_hash(rev):
    return git(f"git -C lean4 rev-parse --short {rev}:stage0")

def is_flags_only(rev):
    diff_output = git(f"git -C lean4 diff --name-only {rev}^..{rev} -- stage0")
    return diff_output == "stage0/src/stdlib_flags.h"

def is_clean(rev):
    changed_files = git(f"git -C lean4 diff --name-only {rev}^..{rev}").split("\n")
    return all(f.startswith("stage0") for f in changed_files)

def main():
    for realrev in bad_squashes.values():
        git(f"git cat-file -e {realrev} || git -C lean4 fetch origin {realrev}")

    todo = git_log("master -- stage0")
    while todo:
        rev = todo.pop(0)
        if rev in bad_squashes:
            todo = git_log(f"{bad_squashes[rev]} -- stage0")
            realrev = todo.pop(0)
        else:
            realrev = rev
        tree_hash = get_tree_hash(realrev)
        flags_only = is_flags_only(realrev)
        clean = flags_only or is_clean(realrev)
        print(f"{rev},{realrev},{tree_hash},{flags_only},{clean}")

if __name__ == "__main__":
    main()

# git -C lean4 log --pretty='tformat:%h' --first-parent --topo-order master -- stage0 |
# while read -r rev ; do
#     tree=$(git -C lean4 rev-parse --short "$rev":stage0)
#     flags_only=false
#     clean=true

#     if [ "$(git -C lean4 diff --name-only "$rev^..$rev" stage0)" = "stage0/src/stdlib_flags.h" ]
#     then
#         flags_only=true
#     elif [ -n "$(git -C lean4 diff --name-only "$rev^..$rev" | grep -v ^stage0)" ]
#     then
#         clean=false
#     fi
#     echo "$rev,$tree,$flags_only,$clean"
# done
