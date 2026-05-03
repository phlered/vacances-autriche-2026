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

# Convert markdown to HTML while preserving HTML blocks
html_content = md_content

# Protect HTML content (iframes, all HTML tags)
protected = {}
counter = 0

# Protect iframes and any HTML tags (they shouldn't be converted)
def protect_html(text):
    global counter
    def replace_match(match):
        global counter
        key = f'___PROTECTED_{counter}___'
        protected[key] = match.group(0)
        counter += 1
        return key
    # Match any HTML tags including iframes
    text = re.sub(r'<[^>]+(?:>.*?</[^>]+>|/>)', replace_match, text, flags=re.DOTALL)
    return text

html_content = protect_html(html_content)

# Simple markdown conversion
html_content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
html_content = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html_content)
html_content = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1">', html_content)
html_content = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html_content)
html_content = re.sub(r'^\* (.*?)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)

# Restore protected content BEFORE wrapping in paragraphs
for key, value in protected.items():
    html_content = html_content.replace(key, value)

# Combine and write output
output_html = head_part + '\n' + html_content + tail_part

write_file('index.html', output_html)
write_file('planning.html', output_html)

print('✓ Updated index.html and planning.html from planning.md')
