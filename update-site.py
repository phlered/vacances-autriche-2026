#!/usr/bin/env python3
"""
Convert planning.md to index.html and planning.html
Preserves the HTML head section from index.html as template
"""

import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Read planning.md content
md_content = read_file('planning.md')

# Read index.html to extract head only
html_template = read_file('index.html')

# Extract everything up to and including <body...> tag
head_match = re.search(r'(.*?<body[^>]*>)', html_template, re.DOTALL)
if not head_match:
    print('Error: Could not find body tag in index.html')
    exit(1)

head_part = head_match.group(1)
tail_part = '</body>\n</html>'

# Split markdown by iframes - this preserves them exactly
# Split on the opening iframe tag
parts = re.split(r'(<iframe\s[^>]*>.*?</iframe>)', md_content, flags=re.DOTALL)

# Process parts: odd indices are iframes (preserve), even indices are markdown (convert)
html_parts = []
for i, part in enumerate(parts):
    if i % 2 == 1:  # This is an iframe - keep as-is
        html_parts.append(part)
    else:  # This is markdown - convert it
        # Convert markdown to HTML
        text = part
        
        # Headings (must be before link conversion to avoid conflict with #)
        text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # Images before links to avoid conflicts
        text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1">', text)
        
        # Links
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
        
        # Bold
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', text)
        
        # Italic
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.*?)_', r'<em>\1</em>', text)
        
        # List items
        text = re.sub(r'^\* (.*?)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        
        html_parts.append(text)

html_content = ''.join(html_parts)

# Combine head + content + tail
output_html = head_part + '\n' + html_content + tail_part

write_file('index.html', output_html)
write_file('planning.html', output_html)

print('✓ Updated index.html and planning.html from planning.md')
