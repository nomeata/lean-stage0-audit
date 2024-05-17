#!/usr/bin/env python

import csv
from collections import defaultdict

digest = list(csv.reader(open('repo-digest.csv', 'r')))
with_nix = csv.reader(open('builds.csv', 'r'))

builds = defaultdict(dict)
for (rev, before, tree) in with_nix:
    builds[rev][before] = tree

revdata = []
to_run = []

for i in range(len(digest)-1):
    (masterrev, rev, stage0_expt, flags_only, clean) = digest[i]
    parent_tree = digest[i+1][2]
    stage0_parent = builds[rev].get(parent_tree)

    data = {
        "masterrev": masterrev,
        "rev": rev,
        "stage0_expt": stage0_expt,
        "flags_only": flags_only == "True",
        "clean": clean == "True",
        "parent_tree": parent_tree,
        "stage0_parent": builds[rev].get(parent_tree),
        "good": False,
        "stage0_alt_src": None,
        "stage0_alt": None,
    }

    if stage0_parent == stage0_expt:
        data["good"] = True

    if stage0_parent is None:
        to_run.append((rev, parent_tree))

    revdata.append(data)



# retrace history, remembering root and derived trees
roots = set()
derived = set()

stage0_current = None
for i in reversed(range(len(revdata))):
    rev = revdata[i]["rev"]
    if stage0_current is not None:
        if revdata[i]["parent_tree"] != stage0_current:
            revdata[i]["stage0_alt_src"] = stage0_current
            revdata[i]["stage0_alt"] = builds[rev].get(stage0_current)
            if revdata[i]["stage0_alt"] == revdata[i]["stage0_expt"]:
                revdata[i]["good"] = True
            if revdata[i]["stage0_alt"] is None:
                to_run = [(rev, stage0_current)] + to_run

    if revdata[i]["stage0_alt"] is not None and revdata[i]["stage0_alt"] != "failed":
        next = revdata[i]["stage0_alt"]
    elif revdata[i]["stage0_parent"] is not None and revdata[i]["stage0_parent"] != "failed":
        next = revdata[i]["stage0_parent"]
    else:
        next = revdata[i]["stage0_expt"]

    if builds[rev].get(stage0_current) == next:
        derived.add(next)
    else:
        roots.add(next)
    stage0_current = next


for rev, tree in to_run[:1]:
    open("next-step.sh","w").write(f"./build.sh {rev} {tree}\\n")


print('''
    <!doctype html>
    <html lang="en">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/chota@latest">
    <style>
    @import url('https://cdnjs.cloudflare.com/ajax/libs/juliamono/0.051/juliamono.css');
    :root {
    --font-family-mono: 'JuliaMono', monospace;
    }
    /*
    tr.good {  background-color: #e6ffe6; }
    tr.boring {  background-color: #EEE; }
    */
    td.derived {  background-color: #e6ffe6; }
    td.root {  background-color: #E33; }
    td { white-space:nowrap; }
    td:last-child { width:100%; }
    </style>
    <title>Lean stage0 audit</title>
    <body>

    <main class="container">
    <h1>Lean stage0 audit</h1>

    <h2>Problem</h2>
    <p>
    Lean is a self-hosting compiler, written in Lean, and compiling Lean to C. Therefore, the lean4
    repository contains a copy of the C files of the compiler itself (in the <code>stage0/</code>
    directory), so that developers have something to start with. 
    </p>
    <p>
      Every now and then, this copy is updated with the output of compiling the current Lean sources.
      These commits are normally labeled <code>chore: stage0 update</code>. Sometimes they are done
      automatically by a Github action, sometimes done by a developer manually.
    </p>
    <p>
      Theoretically, a crafty developer could inject malicious code into this directory, and if that
      malicious code then injects itself in the stage0 compiler’s output, it would surive the
      subsequent updates. This attack vector is described in the “Reflections on Trusting Trust”
      paper by Ken Thompson.
    </p>
    <p>
      This page is an attempt to reproduce and thus audit stage0 updates in lean, to rule out such
      an attack. Ideally, it would suffice to go through every such update, re-run the stage0 update
      from the commit before, and check that the output matches the claimed output.
    </p>
    <p>
      Unfortunately, there are a number of reasons why this may fail:
    </p>
    <ul>
      <li>
      There are files in the stage0 folder that are meant to be edited manually, in particular
      <code>src/stdlib_flags.h</code>..
      </li>
      <li>
      Sometimes a PR comprises of multiple commits with a stage0 update in the middle.
      These are meant to be merged by rebasing. If the feature branch was not up to date with
      <code>master</code>, the rebased sources will now contain new features, but not the rebased
      stage0 copy.
      </li>
      <li>
      Sometimes such a PR is accidentially not merged by rebase, but rather by squashing. Now the stage0
      update is mixed with the source changes.
      </li>
    </ul>

    <h2>Methodology</h2>

    <p>Also see the <a href="https://github.com/nomeata/lean-stage0-audit">Github repo <code>nomeata/lean-stage0-audit</code></a>.</p>

    <ol>
    <li>
      The history of <code>stage0</code>-affecting commits is collected (<code>enum-hashes.py</code>).
    </li>
    <li>
      For each of these commits, the content of <code>stage0</code> is identified (we use the git tree object hash).
    </li>
    <li>
      For each such commit, we try to reproduce the <code>stage0</code> directory by replacing that directory by
      the previous <code>stage0</code> content and running <code>nix run .#update-stage0-commit</code>.
    </li>
    <li>
      If this does not reproduce the <code>stage0</code> content, we try to construct an
      “alternative history” where we try to bootstrap the next commit using that code, and so on,
      until it eventually hopefully leads to an “official” stage0 directory again. 
    </li>
    <li>
      Special support exists for <code>stage0/src/stdlibs.h</code> handling: When reproducing such a
      commit, nothing is built, but we just copy that file.
    </li>
    <li>
      The file <code>bad-squashes.csv</code> implements a form of commit grafting: It maps commits
      on master to alternative commits to use in their stead (e.g. from a feature branch, or
      possibly commits created purely for the purpose of this tool.)
    </li>
    <li>
      The file <code>builds.csv</code> records “input commit”, “stage0 used”, “stage0 produced” triples.
    </li>
    </ol>

    <h2>Legend</h2>

    <ul>
      <li>rev: stage0 changing commit. If this is a grafted commit, original commit in parentheses.</li>
      <li>claim: stage0 as recorded in the commit</li>
      <li>from parent: stage0 of parent and, after ⟹, result of building a new stage0.</li>
      <li>from alt.: stage0 of parent in the “alternative history” and, after ⟹, result of building a new stage0.</li>
      <li>✓: produces same stage0 as claimed </li>
      <li>failed: build attempted but failed</li>
      <li>⌛: build not attepmted yet</li>
      <li>🏁: only stdflags.h is changed</li>
      <li>⚠: commit mixes stage0 and other changes</li>
      <li>⮌: commit was replaced by another commit</li>
      <li>red cell: this is the beginning of a chain of reproduced stage0</li>
      <li>green cell: this stage0 is can be tracted to an earlier version</li>
    </ul>

    <h2>Todo/Help</h2>

    <p>This is a side project of Joachim Breitner, working on it on and off, so some things are
    obviously missing. Help welcome.<p>
    <ul>
    <li>Automate attempting builds and rebuilding this status page on Github Actions.</li>
    <li>Storing the stage0 directories that we produced and that are no on the official repository in some fork.</li>
    <li>Investigate the red, trying to reproduce its stage0 (or a later one) using an earlier one.</li>
    </ul>
    <p>
    In particular with the last point help is welcome. Check out the a commit with a red cell and
    see if you can build it with a green stage0 from before. Any changes to the code outside stage0
    to achieve that is ok, and it can be multiple commits. Reach out to Joachim Breitner on Zulip if
    you have someting to share.
    </p>

    <h2>The audit</h2>

    <div style="overflow-x:auto">
    <table>
    <thead>
    <tr>
    <th>status</th>
    <th>rev</th>
    <th>claim</th>
    <th>from parent</th>
    <th>from alt.</th>
    <th></th>
    </tr>
    </thead>
    <tbody>
    ''')

def revlink(rev):
    return  f'''<a href="https://github.com/leanprover/lean4/commit/{rev}">🔗</a>&nbsp;<code>{rev}</code>'''

def tree(t):
    # return f'''🌲&nbsp;<code>{t}</code>'''
    return f'''<code>{t}</code>'''

def tdclass(s,t):
    if t in roots:
        return 'class="root"'
    if (s in roots or s in derived) and t in derived:
        return 'class="derived"'
    return ''

for d in revdata:
    status = ""
    #clas = "good" if d["good"] else "boring" if d["flags_only"] else "unknown"
    repr_tree = "?"
    built_with = "?"
    comment = ""

    if d['masterrev'] != d['rev']:
        status += " <span title=\"manual replacement\">⮌</a>"
    if d['flags_only']:
        status += " <span title=\"stdflags.h update\">🏁</a>"
    if not d['clean']:
        status += " <span title=\"non-stage0 changes in commit\">⚠</a>"

    print(f'''
    <tr>
    <td>{status}</td>
    <td>{revlink(d['rev'])}''')
    if d['masterrev'] != d['rev']:
        print(f'''&nbsp;({revlink(d['masterrev'])})''')
    print(f'''</td>
    <td {tdclass(None,d['stage0_expt'])}>{tree(d['stage0_expt'])}</td>
    ''')

    print(f'''<td {tdclass(d['parent_tree'],d['stage0_parent'])}>''')
    print(f'''{tree(d['parent_tree'])} ⟹ ''')
    if d['stage0_parent'] is None:
        print(f'''<span title="build pending">⌛</span>''')
    elif d['stage0_parent'] == "failed":
        print(f'''<span title="build failed">☹</span>''')
    elif d['stage0_expt'] == d['stage0_parent']:
        print(f'''<span title="as claimed">✔</span>''')
    else:
        print(f'''{tree(d['stage0_parent'])}''')
    print(f'''</td>''')

    if d.get('stage0_alt_src') is None:
        print(f'''<td />''')
    else:
        print(f'''<td {tdclass(d['stage0_alt_src'],d['stage0_alt'])}>''')
        print(f'''{tree(d['stage0_alt_src'])} ⟹ ''')

        if d.get('stage0_alt') is None:
            print(f'''<span title="build pending">⌛</span>''')
        elif d['stage0_alt'] == "failed":
            print(f'''<span title="build failed">☹</span>''')
        elif d['stage0_expt'] == d['stage0_alt']:
            print(f'''<span title="as claimed">✔</span>''')
        else:
            print(f'''{tree(d['stage0_alt'])}''')
        print(f'''</td>''')
        
    print(f'''
    <td/>
    </tr>
    ''')

print('''
    </tbody>
    </table>
    <h2>Next steps</h2>
    <pre>
''')
for (rev, tree) in to_run[:20]:
    print(f"./build.sh {rev} {tree}")
print('''
    </pre>
''')
if len(to_run) > 20:
    print(f'''<p>(And {len(to_run)-20} more.)</p>''')
print('''
    </div>
    </main>
    </body>
    </html>
    ''')
