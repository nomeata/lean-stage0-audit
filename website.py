#!/usr/bin/env python

import csv

digest = csv.reader(open('repo-digest.csv', 'r'))
with_nix = csv.reader(open('with-nix.log', 'r'))

naive = {}
for (rev, _, before, tree) in with_nix:
    naive[rev] = (before, tree)

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
    tr.good {  background-color: #e6ffe6; }
    tr.boring {  background-color: #EEE; }
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
    <th>expt. stage0</th>
    <th>repr. stage0</th>
    <th>built with</th>
    <th>comment</th>
    </tr>
    </thead>
    <tbody>
    ''')

for (rev, expt_tree, before, clean) in digest:
    status = "?"
    clas = "unknown"
    repr_tree = "?"
    built_with = "?"
    comment = ""

    if before:
        status = "…"
        clas = "boring"
        repr_tree = expt_tree
        built_with = before
        comment = f"(stdlib_flags.h only)"
    else:
        if rev in naive:
            (built_with, repr_tree) = naive[rev]
            if repr_tree == "failed":
                status = "☹"
                built_with = ""
                comment = "(rebootstrap failed)"
            elif repr_tree == expt_tree:
                status = "✓"
                clas = "good"
                comment = "(rebootstrap succeeded)"
            else:
                status = "😕"
                comment = "(rebootstrap differs)"

        if clean != "true":
            status += " <span title=\"non-stage0 chnages in commit\">⚠</a>"

    print(f'''
    <tr class="{clas}">
    <td>{status}</td>
    <td><a href="https://github.com/leanprover/lean4/commit/{rev}"><code>{rev}</code></a></td>
    <td><code>{expt_tree}</code></td>
    <td><code>{repr_tree}</code></td>
    <td><code>{built_with}</code></td>
    <td>{comment}</td>
    </tr>
    ''')

print('''
    </tbody>
    </table>
    </div>
    </main>
    </body>
    </html>
    ''')
