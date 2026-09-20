"""检查真实浏览器往返产物中的文字可编辑性、对齐和字重，不只核对文本数量。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from lxml import html


def content(element):
    return element.get('content') or element.get('text', {}).get('content') or ''


def plain(raw):
    return re.sub(r'\s+', '', html.fragment_fromstring(raw, create_parent='div').text_content()) if raw else ''


def style(raw, property_name, default):
    values = re.findall(rf'{re.escape(property_name)}\s*:\s*([^;"\s]+)', raw)
    return values[-1] if values else default


def bold(raw):
    return bool(re.search(r'<(?:strong|b)(?:\s|>)', raw)) or style(raw, 'font-weight', 'normal') in {'bold', '600', '700', '800', '900'}


def verify(state):
    checked = 0
    failures = []
    if len(state['expected']) != len(state['actual']):
        failures.append({'issue': '页数变化'})
    for i, (source, target) in enumerate(zip(state['expected'], state['actual']), 1):
        for element in source['elements']:
            raw = content(element)
            if not plain(raw):
                continue
            matches = [e for e in target['elements'] if plain(content(e)) == plain(raw)]
            if not matches:
                failures.append({'slide': i, 'element': element['id'], 'issue': '缺少原生可编辑文字'})
                continue
            actual = content(matches[0])
            checked += 1
            for name, expected, found in [('align', style(raw, 'text-align', 'left'), style(actual, 'text-align', 'left')), ('bold', bold(raw), bold(actual))]:
                if expected != found:
                    failures.append({'slide': i, 'element': element['id'], 'issue': name, 'expected': expected, 'actual': found})
    return {'status': 'PASS' if not failures else 'FAIL', 'editableTextObjectsChecked': checked, 'failures': failures}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('state', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = verify(json.loads(args.state.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checked': result['editableTextObjectsChecked'], 'failures': len(result['failures'])}))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
