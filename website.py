#!/usr/bin/env python

import csv

# Open the CSV file
digest = csv.reader(open('repo-digest.csv', 'r'))
for (rev, tree) in digest:
    print (rev,tree)