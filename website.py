#!/usr/bin/env python

import csv
from collections import defaultdict

digest = list(csv.reader(open('repo-digest.csv', 'r')))
with_nix = csv.reader(open('with-nix.log', 'r'))

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

    <div style="overflow-x:auto">
    <table>
    <thead>
    <tr>
    <th>status</th>
    <th>rev</th>
    <th>claim</th>
    <th>from parent</th>
    <th>from alt.</th>
    <th>comment</th>
    </tr>
    </thead>
    <tbody>
    ''')

def revlink(rev):
    return  f'''<a href="https://github.com/leanprover/lean4/commit/{rev}">🔗</a>&nbsp;<code>{rev}</code>'''

def tree(t):
    # return f'''🌲&nbsp;<code>{t}</code>'''
    return f'''<code>{t}</code>'''

def tdclass(t):
    if t in roots:
        return 'class="root"'
    if t in derived:
        return 'class="derived"'
    return ''

for d in revdata:
    status = "✓" if d["good"] else "?"
    clas = "good" if d["good"] else "boring" if d["flags_only"] else "unknown"
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
    <tr class="{clas}">
    <td>{status}</td>
    <td>{revlink(d['rev'])}''')
    if d['masterrev'] != d['rev']:
        print(f'''&nbsp;({revlink(d['masterrev'])})''')
    print(f'''</td>
    <td {tdclass(d['stage0_expt'])}>{tree(d['stage0_expt'])}</td>
    ''')

    print(f'''<td {tdclass(d['stage0_parent'])}>''')
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
        print(f'''<td {tdclass(d['stage0_alt'])}>''')
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
    <h3>Next steps</h3>
    <pre>
''')
for (rev, tree) in to_run[:20]:
    print(f"./with-nix.sh {rev} {tree}")
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
