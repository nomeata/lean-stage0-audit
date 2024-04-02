#!/usr/bin/env python

import csv

digest = csv.reader(open('repo-digest.csv', 'r'))

# parse file names in 
import os
import re

reproducers = {}
stage0_files = os.listdir('stage0/')
for filename in stage0_files:
    match = re.match(r'(.+)-from-(.+)\.sh', filename)
    if match:
        reproducers[match.group(1)] = match.group(2)

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
    <th>stage0</th>
    <th>comment</th>
    </tr>
    </thead>
    <tbody>
    ''')

for (rev, tree, before, clean) in digest:
    status = "?"
    good = False
    comment = ""
    if before:
        status = "✓"
        good = True
        comment = f"← <code>{before}</code> (stdlib_flags.h only)"
    elif tree in reproducers:
        status = "✓"
        good = True
        comment = f"← <code>{reproducers[tree]}</code> (nix)"
    if clean != "true":
        status += " <span title=\"non-stage0 chnages in commit\">⚠</a>"

    print(f'''
    <tr class="{"good" if good else "unknown"}">
    <td>{status}</td>
    <td><code>{rev}</code></td>
    <td><code>{tree}</code></td>
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
