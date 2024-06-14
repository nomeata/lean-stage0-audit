#!/usr/bin/env python3

import subprocess
import csv

bad_squashes = dict(csv.reader(open('bad-squashes.csv', 'r')))

def git(command):
    return subprocess.check_output(command, shell=True).decode().strip()

def git_log(arg):
    # rev 2794ae76 introduced the nix-based stage0 update;
    # ignore older commits until the build.sh script can handle it
    return [l.split(";") for l in git(f"git -C lean4 log --pretty='tformat:%h;%cs' --first-parent --topo-order ^2794ae76 " + arg).split("\n")]

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
        git(f"git -C lean4 cat-file -e {realrev} || git -C lean4 fetch origin {realrev}")

    todo = git_log("master -- stage0")
    master_revs = set(rev for rev,date in todo)
    while todo:
        rev, date = todo.pop(0)
        if rev in bad_squashes:
            todo = git_log(f"{bad_squashes[rev]} -- stage0")
            realrev, date = todo.pop(0)
        else:
            realrev = rev
        tree_hash = get_tree_hash(realrev)
        flags_only = is_flags_only(realrev)
        clean = flags_only or is_clean(realrev)
        on_master = realrev in master_revs
        print(f"{date},{rev},{realrev},{tree_hash},{flags_only},{clean},{on_master}")

if __name__ == "__main__":
    main()
