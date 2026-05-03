#!/usr/bin/env python3
"""
Convert planning.md to index.html.
Uses template.html for the shared HTML shell.
"""

import argparse
import re
import subprocess
import sys


FILES_TO_STAGE = [
    'planning.md',
    'template.html',
    'styles.css',
    'update-site.py',
    'index.html',
]

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate index.html from planning.md.'
    )
    parser.add_argument(
        '--no-push',
        action='store_true',
        help='Generate index.html without committing or pushing changes.',
    )
    parser.add_argument(
        '--message',
        default='Update site',
        help='Commit message to use for the automatic commit.',
    )
    return parser.parse_args()


def run_command(command):
    subprocess.run(command, check=True)


def commit_and_push(commit_message):
    try:
        run_command(['git', 'add', *FILES_TO_STAGE])

        staged_changes = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            check=False,
        )
        if staged_changes.returncode == 0:
            print('✓ No changes to commit')
            return

        run_command(['git', 'commit', '-m', commit_message])
        run_command(['git', 'push'])
        print('✓ Committed and pushed changes')
    except subprocess.CalledProcessError as exc:
        print(f'Error: git command failed with exit code {exc.returncode}')
        sys.exit(exc.returncode)


args = parse_args()

# Read planning.md content
md_content = read_file('planning.md')

# Read template.html to extract the HTML shell
html_template = read_file('template.html')

# Extract everything up to and including <body...> tag
head_match = re.search(r'(.*?<body[^>]*>)', html_template, re.DOTALL)
if not head_match:
    print('Error: Could not find body tag in template.html')
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
        
        # Links with markdown syntax
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
        
        # Bare URLs - convert to clickable links
        text = re.sub(r'(?<!href=")(?<!href=\')(?<!>)(https?://[^\s<>]+)', r'<a href="\1">\1</a>', text)
        
        # Bold
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', text)
        
        # Italic
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        
        # List items
        text = re.sub(r'^\* (.*?)$', r'<li>\1</li>', text, flags=re.MULTILINE)

        # Build block-level HTML so line breaks are visible in browser rendering.
        lines = text.splitlines()
        rendered_lines = []
        in_list = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if in_list:
                    rendered_lines.append('</ul>')
                    in_list = False
                rendered_lines.append('')
                continue

            if re.match(r'^<li>.*</li>$', stripped):
                if not in_list:
                    rendered_lines.append('<ul>')
                    in_list = True
                rendered_lines.append(stripped)
                continue

            if in_list:
                rendered_lines.append('</ul>')
                in_list = False

            if re.match(r'^<(h1|h2|h3|img|iframe|ul|/ul|li|/li|p|/p|em|strong|a)(\s|>|/)', stripped):
                rendered_lines.append(stripped)
            else:
                rendered_lines.append(f'<p>{stripped}</p>')

        if in_list:
            rendered_lines.append('</ul>')

        text = '\n'.join(rendered_lines)
        
        html_parts.append(text)

html_content = ''.join(html_parts)

# Combine head + content + tail
output_html = head_part + '\n' + html_content + tail_part

write_file('index.html', output_html)

print('✓ Updated index.html from planning.md')

if not args.no_push:
    commit_and_push(args.message)
