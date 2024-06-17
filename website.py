#!/usr/bin/env python

import csv
from collections import defaultdict

digest = list(csv.reader(open('repo-digest.csv', 'r')))
with_nix = csv.reader(open('builds.csv', 'r'))

builds = defaultdict(dict)
urls = defaultdict(dict)
for (rev, before, tree, url) in with_nix:
    builds[rev][before] = tree
    urls[rev][before] = url

revdata = []
to_run = []

for i in range(len(digest)-1):
    (date, masterrev, rev, stage0_expt, flags_only, clean, on_master) = digest[i]
    parent_tree = digest[i+1][3]
    stage0_parent = builds[rev].get(parent_tree)

    data = {
        "date": date,
        "masterrev": masterrev,
        "rev": rev,
        "stage0_expt": stage0_expt,
        "flags_only": flags_only == "True",
        "clean": clean == "True",
        "on_master": on_master == "True",
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

def is_root_rev(i):
    r = revdata[i]
    return not (r["stage0_expt"] in derived or r["stage0_alt"] in derived or r["stage0_parent"] in derived)

# find the first interesting from bottom
for i in reversed(range(len(revdata))):
    if not is_root_rev(i):
        last_looked_at = i+1
        break

root_revs = [ i for i in range(last_looked_at+1) if is_root_rev(i) ]
# find the starting point
first_steps = root_revs[0]
first_rev = revdata[first_steps]["rev"]
first_date = revdata[first_steps]["date"]

# find the last
todo_revs = len(root_revs)-1
last_steps = root_revs[-1]
last_rev = revdata[last_steps]["rev"]
last_date = revdata[last_steps]["date"]

for rev, tree in to_run[:1]:
    open("next-step.sh","w").write(f"./build.sh {rev} {tree}\n")

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
    td.grafted { text-decoration: line-through }

    summary h2 { display: inline-block };
    </style>
    <title>Lean stage0 audit</title>
    <body>

    <main class="container">
    <h1>Lean stage0 audit</h1>

    <h2>Current status</h2>
''')
print(f'''
    <p>The current <code>stage0/</code> code copy can be traced to <code>stage0/</code> in <a href="#{first_rev}">revision ✨ <code>{first_rev}</code></a> from {first_date} in {first_steps} steps.</p>
    <p>Investigating {todo_revs} revisions will trace it to <a href="#{last_rev}">revision <code>{last_rev}</code></a> from {last_date} in {last_steps} steps.</p>
''')

print('''
    <details>
    <summary><h2>The Problem</h2></summary>
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
      <li>
      Sometimes one of the flags in <code>stage0/src/stdlib_flags.h</code> is
      set, but this change is not committed before the next stage0 update.
      </li>
    </ul>
    </details>

    <details>
    <summary><h2>Methodology</h2></summary>

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
      possibly commits created purely for the purpose of this audit).
    </li>
    <li>
      The file <code>builds.csv</code> records “input commit”, “stage0 used”, “stage0 produced (or `failed`)”, “log url” tuples.
    </li>
    <li>
      The produced <code>stage0/</code> trees, which may not exist as such in the main lean4 repository,
      are stored in this git repository under <code>refs/stage0/&lt;short tree hash&gt;</code>. This allows
      the reproduction of each individual step even in a long “alternative” chain.
    </li>
    <li>
      A <a href="https://github.com/nomeata/lean-stage0-audit/actions/workflows/next-step.yml">scheduled Github action</a>
      is auditing new commits, and also (slowly) goes back further through the project history.
    </li>
    </ol>
    </details>

    <details>
    <summary><h2>Legend</h2></summary>

    <ul>
      <li>rev: stage0 changing commit on the master branch.</li>
      <li>graft: if the commit has been grafted, the actual commits considered.</li>
      <li>claim: stage0 as recorded in the commit</li>
      <li>from parent: stage0 of parent and, after ⟹, result of building a new stage0.</li>
      <li>from alt.: stage0 of parent in the “alternative history” and, after ⟹, result of building a new stage0.</li>
      <li>✓: produces same stage0 as claimed</li>
      <li>(✓): produces same stage0 as reproduced from parent commit </li>
      <li>☹: build attempted but failed (may link to build log)</li>
      <li>⌛: build not attepmted yet</li>
      <li>🏁: only stdflags.h is changed</li>
      <li>⚠: commit mixes stage0 and other changes</li>
      <li>red cell: this is the beginning of a chain of reproduced stage0</li>
      <li>green cell: this stage0 is can be tracted to an earlier version</li>
      <li>✨: commit to trust to reproduce the latest stage0</li>
    </ul>
    </details>

    <details>
    <summary><h2>Todo/Help</h2></summary>

    <p>This is a side project of Joachim Breitner, working on it on and off, so some things are
    obviously missing. Help welcome.
    </p>
    <p>
    In particular you can push back the beginning of reproducibility: If there is a row with a
    red cell in the table blow, Check out the a commit with a red cell and
    see if you can build it with a green stage0 from before. Any changes to the code outside stage0
    to achieve that is ok, and it can be multiple commits.
    </p>
    <p>
    Reach out to Joachim Breitner on Zulip if you have questions or new results.
    </p>
    </details>

    <h2>The audit</h2>

    <div style="overflow-x:auto">
    <table>
    <thead>
    <tr>
    <th>status</th>
    <th>rev</th>
    <th>graft</th>
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

    if d['flags_only']:
        status += " <span title=\"stdflags.h update\">🏁</a>"
    if not d['clean']:
        status += " <span title=\"non-stage0 changes in commit\">⚠</a>"

    if d['rev'] == first_rev:
        status += "<span title=\"earliest root of trust\">✨</a>"

    print(f'''
    <tr>
    <td><a name="{d['rev']}"/>{status}</td>
    ''')
    if d['masterrev'] != d['rev']:
      print(f'''
      <td class="grafted">{revlink(d['masterrev'])}</td>
      <td>{revlink(d['rev'])}</td>
      ''')
    elif d['on_master']:
      print(f'''
      <td>{revlink(d['masterrev'])}</td>
      <td/>
      ''')
    else:
      print(f'''
      <td/>
      <td>{revlink(d['rev'])}</td>
      ''')
    print(f'''
    <td {tdclass(None,d['stage0_expt'])}>{tree(d['stage0_expt'])}</td>
    ''')

    print(f'''<td {tdclass(d['parent_tree'],d['stage0_parent'])}>''')
    print(f'''{tree(d['parent_tree'])} ⟹ ''')
    if d['stage0_parent'] is None:
        print(f'''<span title="build pending">⌛</span>''')
    elif d['stage0_parent'] == "failed":
        if d['parent_tree'] in urls[d['rev']]:
            print(f'''<a href="{urls[d["rev"]][d["parent_tree"]]}" title="build failed">☹</a>''')
        else:
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
            if d['stage0_alt_src'] in urls[d['rev']]:
                print(f'''<a href="{urls[d["rev"]][d["stage0_alt_src"]]}" title="build failed">☹</a>''')
            else:
                print(f'''<span title="build failed">☹</span>''')
        elif d['stage0_expt'] == d['stage0_alt']:
            print(f'''<span title="as claimed">✔</span>''')
        elif d['stage0_parent'] == d['stage0_alt']:
            print(f'''<span title="as reproduced from parent">(✔)</span>''')
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
