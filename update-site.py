#!/usr/bin/env python3
"""
Generate index.html and planning.pdf from planning.md.
Uses template.html for the HTML shell.
Adds a clickable QR code next to each HTTP/HTTPS link.
"""

import argparse
import base64
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import markdown
import qrcode
from bs4 import BeautifulSoup
from bs4 import NavigableString


FILES_TO_STAGE = [
    'planning.md',
    'template.html',
    'styles.css',
    'print.css',
    'update-site.py',
    'index.html',
    'planning.pdf',
]


def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate index.html and planning.pdf from planning.md.'
    )
    parser.add_argument(
        '--no-push',
        action='store_true',
        help='Generate files without committing or pushing changes.',
    )
    parser.add_argument(
        '--message',
        default='Update site',
        help='Commit message to use for the automatic commit.',
    )
    parser.add_argument(
        '--no-pdf',
        action='store_true',
        help='Generate index.html only (skip planning.pdf generation).',
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
            print('No changes to commit')
            return

        run_command(['git', 'commit', '-m', commit_message])
        run_command(['git', 'push'])
        print('Committed and pushed changes')
    except subprocess.CalledProcessError as exc:
        print(f'Error: git command failed with exit code {exc.returncode}')
        sys.exit(exc.returncode)


def extract_html_shell(template_content):
    match = re.search(r'(.*?<body[^>]*>)(.*?)(</body>\s*</html>)', template_content, re.DOTALL)
    if not match:
        print('Error: Could not parse template.html body structure')
        sys.exit(1)
    return match.group(1), match.group(3)


def preserve_iframes(markdown_text):
    token_map = {}

    def _replace(match):
        token = f'IFRAME_TOKEN_{len(token_map)}'
        token_map[token] = match.group(0)
        return token

    protected = re.sub(r'<iframe\s[^>]*>.*?</iframe>', _replace, markdown_text, flags=re.DOTALL)
    return protected, token_map


def restore_iframes(html_text, token_map):
    restored = html_text
    for token, iframe_html in token_map.items():
        restored = restored.replace(f'<p>{token}</p>', iframe_html)
        restored = restored.replace(token, iframe_html)
    return restored


def make_qr_data_uri(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    encoded = base64.b64encode(buf.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def add_clickable_qr_codes(full_html):
    soup = BeautifulSoup(full_html, 'html.parser')
    qr_cache = {}

    url_pattern = re.compile(r'(https?://[^\s<]+)')

    for text_node in soup.find_all(string=True):
        if not isinstance(text_node, NavigableString):
            continue
        parent = text_node.parent
        if parent and parent.name in ('a', 'script', 'style', 'code', 'pre'):
            continue

        original = str(text_node)
        if 'http://' not in original and 'https://' not in original:
            continue

        parts = url_pattern.split(original)
        if len(parts) == 1:
            continue

        new_nodes = []

        for index, part in enumerate(parts):
            if part == '':
                continue
            if index % 2 == 1:
                link_node = soup.new_tag('a', href=part)
                link_node.string = part
                new_nodes.append(link_node)
            else:
                new_nodes.append(NavigableString(part))

        if new_nodes:
            text_node.replace_with(new_nodes[0])
            current = new_nodes[0]
            for node in new_nodes[1:]:
                current.insert_after(node)
                current = node

    for link in soup.find_all('a', href=True):
        href = link.get('href', '').strip()
        if not href.startswith(('http://', 'https://')):
            continue

        if 'qr-link' in (link.get('class') or []):
            continue

        if href not in qr_cache:
            qr_cache[href] = make_qr_data_uri(href)

        qr_anchor = soup.new_tag('a', href=href)
        qr_anchor['class'] = 'qr-link'
        qr_anchor['target'] = '_blank'
        qr_anchor['rel'] = 'noopener noreferrer'
        qr_anchor['title'] = f'Open {href}'

        qr_img = soup.new_tag('img')
        qr_img['class'] = 'qr-code'
        qr_img['src'] = qr_cache[href]
        qr_img['alt'] = f'QR code for {href}'

        qr_anchor.append(qr_img)
        link.insert_after(qr_anchor)
        qr_anchor.insert_before(' ')

    return str(soup)


def markdown_to_html_body(markdown_text):
    protected_md, token_map = preserve_iframes(markdown_text)
    body_html = markdown.markdown(
        protected_md,
        extensions=['extra', 'tables', 'sane_lists', 'nl2br'],
    )
    return restore_iframes(body_html, token_map)


def build_index_html(markdown_text, template_content):
    head_part, tail_part = extract_html_shell(template_content)
    body_content = markdown_to_html_body(markdown_text)
    base_html = f'{head_part}\n{body_content}\n{tail_part}'
    return add_clickable_qr_codes(base_html)


def parse_komoot_iframe_src(src):
    parsed = urlparse(src)
    match = re.search(r'/tour/(\d+)/embed', parsed.path)
    if not match:
        return None, None
    tour_id = match.group(1)
    query = parse_qs(parsed.query)
    share_token = query.get('share_token', [None])[0]
    return tour_id, share_token


def fetch_komoot_tour_data(tour_id, share_token=None):
    api_url = f'https://www.komoot.com/api/v007/tours/{tour_id}'
    if share_token:
        api_url += f'?share_token={share_token}'

    req = Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=20) as response:
        data = json.loads(response.read().decode('utf-8'))

    map_image_raw = (
        data.get('vector_map_image')
        or data.get('map_image')
        or data.get('vector_map_image_preview')
        or data.get('map_image_preview')
    )
    map_url = None
    if isinstance(map_image_raw, str):
        map_url = map_image_raw
    elif isinstance(map_image_raw, dict):
        map_url = map_image_raw.get('src') or map_image_raw.get('url')
    return {
        'id': tour_id,
        'name': data.get('name') or f'Tour {tour_id}',
        'distance_km': round(float(data.get('distance', 0.0)) / 1000.0, 1),
        'elevation_up': int(round(float(data.get('elevation_up', 0.0)))),
        'elevation_down': int(round(float(data.get('elevation_down', 0.0)))),
        'map_url': map_url,
        'public_url': f'https://www.komoot.com/fr-fr/tour/{tour_id}',
    }


def normalize_komoot_map_url(image_url):
    if not image_url:
        return None

    # Komoot fournit parfois des URLs template avec {width}/{height}/{crop}.
    # On force un rendu HD et non-croppe pour limiter la pixelisation/zoom.
    normalized = image_url
    normalized = normalized.replace('{width}', '1800')
    normalized = normalized.replace('{height}', '1000')
    normalized = normalized.replace('{crop}', 'false')
    return normalized


def fetch_image_data_uri(image_url):
    if isinstance(image_url, dict):
        image_url = image_url.get('src') or image_url.get('url')

    if not image_url or not isinstance(image_url, str):
        return None

    image_url = normalize_komoot_map_url(image_url)

    if not image_url:
        return None
    req = Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=20) as response:
        raw = response.read()

    ext = 'jpeg'
    lowered = image_url.lower()
    if '.png' in lowered:
        ext = 'png'
    elif '.webp' in lowered:
        ext = 'webp'
    encoded = base64.b64encode(raw).decode('ascii')
    return f'data:image/{ext};base64,{encoded}'


def build_komoot_card(soup, iframe_src, cache):
    tour_id, share_token = parse_komoot_iframe_src(iframe_src)
    if not tour_id:
        return None

    cache_key = (tour_id, share_token)
    if cache_key not in cache:
        try:
            tour_data = fetch_komoot_tour_data(tour_id, share_token)
            image_data_uri = fetch_image_data_uri(tour_data.get('map_url'))
            tour_data['image_data_uri'] = image_data_uri
            cache[cache_key] = tour_data
        except Exception:
            cache[cache_key] = None

    tour_data = cache.get(cache_key)
    if not tour_data:
        return None

    card = soup.new_tag('div')
    card['class'] = 'komoot-card'

    title = soup.new_tag('h4')
    title['class'] = 'komoot-title'
    title.string = tour_data['name']
    card.append(title)

    stats = soup.new_tag('p')
    stats['class'] = 'komoot-stats'
    stats.string = (
        f"Distance: {tour_data['distance_km']} km | "
        f"D+ {tour_data['elevation_up']} m | "
        f"D- {tour_data['elevation_down']} m"
    )
    card.append(stats)

    if tour_data.get('image_data_uri'):
        preview = soup.new_tag('img')
        preview['class'] = 'komoot-preview'
        preview['src'] = tour_data['image_data_uri']
        preview['alt'] = f"Carte Komoot {tour_data['name']}"
        card.append(preview)

    footer = soup.new_tag('div')
    footer['class'] = 'komoot-footer'

    link = soup.new_tag('a', href=tour_data['public_url'])
    link['class'] = 'komoot-tour-link'
    link.string = tour_data['public_url']
    footer.append(link)

    qr_anchor = soup.new_tag('a', href=tour_data['public_url'])
    qr_anchor['class'] = 'qr-link komoot-qr-link'
    qr_anchor['target'] = '_blank'
    qr_anchor['rel'] = 'noopener noreferrer'
    qr_anchor['title'] = f"Open {tour_data['public_url']}"

    qr_img = soup.new_tag('img')
    qr_img['class'] = 'qr-code komoot-qr-code'
    qr_img['src'] = make_qr_data_uri(tour_data['public_url'])
    qr_img['alt'] = f"QR code for {tour_data['public_url']}"

    qr_anchor.append(qr_img)
    footer.append(qr_anchor)

    card.append(footer)
    return card


def generate_pdf_from_html(full_html, output_pdf_path):
    soup = BeautifulSoup(full_html, 'html.parser')
    komoot_cache = {}

    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '').strip()
        komoot_card = build_komoot_card(soup, src, komoot_cache)
        if komoot_card is not None:
            iframe.replace_with(komoot_card)
            continue

        replacement = soup.new_tag('p')
        replacement.string = 'Parcours interactif (ouvrir via le lien): '
        if src:
            link = soup.new_tag('a', href=src)
            link.string = src
            link['class'] = 'pdf-fallback-link'
            replacement.append(link)
        iframe.replace_with(replacement)

    temp_html = Path('index.pdf-source.html')
    temp_html.write_text(str(soup), encoding='utf-8')

    browser_candidates = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    ]

    browser_path = None
    for candidate in browser_candidates:
        if Path(candidate).exists():
            browser_path = candidate
            break

    if not browser_path:
        temp_html.unlink(missing_ok=True)
        print('Error: no headless browser found (Chrome/Chromium/Edge).')
        print('PDF was not generated. Install Chrome/Chromium or use --no-pdf.')
        sys.exit(1)

    input_url = f'file://{temp_html.resolve()}'
    command = [
        browser_path,
        '--headless=new',
        '--disable-gpu',
        '--print-to-pdf-no-header',
        f'--print-to-pdf={Path(output_pdf_path).resolve()}',
        input_url,
    ]
    run_command(command)
    temp_html.unlink(missing_ok=True)


def main():
    args = parse_args()

    md_content = read_file('planning.md')
    html_template = read_file('template.html')

    output_html = build_index_html(md_content, html_template)
    write_file('index.html', output_html)
    print('Updated index.html from planning.md (with clickable QR codes on links)')

    if not args.no_pdf:
        generate_pdf_from_html(output_html, 'planning.pdf')
        print('Generated planning.pdf from index.html')

    if not args.no_push:
        commit_and_push(args.message)


if __name__ == '__main__':
    main()
