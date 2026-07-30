"""Structural sanity check for GDScript files.

Not a parser. Catches the mistakes that are easy to make when editing .gd by
hand and impossible to see without Godot: mixed tabs/spaces, a block opener
with no indented body, unbalanced brackets, and indentation that jumps by
more than one level.

Physical lines are joined into logical ones first. Without that, the closing
line of a wrapped `func` signature looks like a fresh block opener and every
subsequent indentation check drifts.
"""

import glob
import os
import re
import sys

BLOCK_OPENER = re.compile(
    r'^\s*(if|elif|else|for|while|match|func|static\s+func|class|class_name|enum)\b'
)
OPENERS = {'(': ')', '[': ']', '{': '}'}
CLOSERS = set(OPENERS.values())


def strip_strings_and_comments(line):
    """Remove string literals and trailing comments so only structure remains."""
    out, i, quote = [], 0, None
    while i < len(line):
        c = line[i]
        if quote:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in '"\'':
            quote = c
            i += 1
            continue
        if c == '#':
            break
        out.append(c)
        i += 1
    return ''.join(out)


def logical_lines(lines):
    """Yield (lineno, indent, code) for each logical line.

    Continuations — inside brackets or after a trailing backslash — are folded
    into the line that started them.
    """
    depth = 0
    in_triple = None
    pending = None

    for n, raw in enumerate(lines, 1):
        # Triple-quoted blocks hold generated GDScript in several files here.
        # Their contents are data, not structure.
        if in_triple:
            if in_triple in raw:
                in_triple = None
            continue
        opened_triple = False
        for marker in ('"""', "'''"):
            if raw.count(marker) == 1:
                in_triple = marker
                opened_triple = True
                break

        if not raw.strip():
            continue

        code = strip_strings_and_comments(raw)
        indent_text = raw[:len(raw) - len(raw.lstrip())]

        if pending is None:
            indent = indent_text.count('\t') + indent_text.count(' ') // 4
            pending = [n, indent, code, indent_text]
        else:
            pending[2] += ' ' + code.strip()

        depth += sum(1 for c in code if c in OPENERS)
        depth -= sum(1 for c in code if c in CLOSERS)

        continues = depth > 0 or code.rstrip().endswith('\\')
        if opened_triple:
            continues = True

        if not continues:
            yield pending[0], pending[1], pending[2], pending[3]
            pending = None

    if pending is not None:
        yield pending[0], pending[1], pending[2], pending[3]
    if depth != 0:
        yield -1, 0, f'__UNBALANCED__{depth}', ''


def check(path):
    problems = []
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')

    prev_indent = 0
    prev_was_opener = False
    prev_lineno = 0

    for lineno, indent, code, indent_text in logical_lines(lines):
        if code.startswith('__UNBALANCED__'):
            problems.append(f'EOF: {code.removeprefix("__UNBALANCED__")} unclosed bracket(s)')
            continue

        if ' ' in indent_text and '\t' in indent_text:
            problems.append(f'{lineno}: mixed tabs and spaces in indentation')
        elif indent_text and '\t' not in indent_text:
            problems.append(f'{lineno}: space indentation (GDScript convention is tabs)')

        if prev_was_opener and indent <= prev_indent:
            problems.append(f'{prev_lineno}: block opener with no indented body')

        if indent > prev_indent + 1:
            problems.append(f'{lineno}: indentation jumps {prev_indent} -> {indent}')

        prev_was_opener = bool(BLOCK_OPENER.match(code)) and code.rstrip().endswith(':')
        prev_indent = indent
        prev_lineno = lineno

    return problems


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    files = sorted(glob.glob(os.path.join(root, '**', '*.gd'), recursive=True))
    if not files:
        print(f'no .gd files under {root}')
        return 1

    total = 0
    for path in files:
        problems = check(path)
        if problems:
            total += len(problems)
            print(f'\n{os.path.relpath(path, root)}')
            for p in problems:
                print(f'  {p}')

    print(f'\nchecked {len(files)} files, {total} structural problems')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
