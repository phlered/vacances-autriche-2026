#!/usr/bin/env python3
"""
Convert planning.md to index.html and planning.html
Preserves the HTML head section and applies responsive mobile styling
"""

import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Read files
md_content = read_file('planning.md')
html_template = read_file('index.html')

# Extract head and opening body tag
head_match = re.search(r'(.*?<body[^>]*>)', html_template, re.DOTALL)
if not head_match:
    print('Error: Could not find body tag')
    exit(1)

head_part = head_match.group(1)
tail_part = '\n</body>\n</html>'

html_content = md_content

# Protect iframes - use simple placeholder approach
iframes = []
def save_iframe(match):
    iframes.append(match.group(0))
    return f'___IFRAME_{len(iframes)-1}___'

# Protect all iframes before markdown processing
html_content = re.sub(r'<iframe[^>]*>.*?</iframe>', save_iframe, html_content, flags=re.DOTALL)

# Simple markdown conversion
html_content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
html_content = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html_content)
html_content = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1">', html_content)
html_content = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html_content)
html_content = re.sub(r'^\* (.*?)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)

# Restore iframes
for i, iframe in enumerate(iframes):
    html_content = html_content.replace(f'___IFRAME_{i}___', iframe)

# Combine and write output
output_html = head_part + '\n' + html_content + tail_part

write_file('index.html', output_html)
write_file('planning.html', output_html)

print('✓ Updated index.html and planning.html from planning.md')
