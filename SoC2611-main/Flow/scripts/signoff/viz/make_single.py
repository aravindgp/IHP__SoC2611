#!/usr/bin/env python3
"""Inline data.js into index.html and wrap it in a complete HTML document -> one self-contained file.
usage: make_single.py <index.html> <data.js> <out.html>"""
import sys

src, data, out = sys.argv[1:4]
page = open(src).read()
js = open(data).read()
page = page.replace('<script src="data.js"></script>', '<script>\n' + js + '</script>')
doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       + page.split('<style>', 1)[0] + '<style>' + page.split('<style>', 1)[1].split('</style>', 1)[0] + '</style>\n</head>\n<body>\n'
       + page.split('</style>', 1)[1] + '\n</body>\n</html>\n')
open(out, 'w').write(doc)
print(f'wrote {out}: {len(doc) // 1024} KB')
