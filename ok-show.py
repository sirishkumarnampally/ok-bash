#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import argparse, codecs, os, re, sys


class ParsedLine:
    INDENT_CHAR=' '
    def __init__(self, t, line, pos=None, line_nr=None):
        self.t = t
        self.line = line
        self.pos = pos
        self.line_nr = line_nr
        self.indent = 0
        self.rpad = 0

    def rpad_to(self, max_width, nr_positions_line_nr):
        rpad_value = max_width - len(self.line) - self.indent
        self.rpad = rpad_value if rpad_value > 0 else 0
        print('{}-rpad: {} (len:{}, indent:{}, nr_positions_line_nr:{})'.format(self.line_nr, rpad_value, len(self.line), self.indent, nr_positions_line_nr))

    def set_indent(self, max_pos):
        self.indent = max_pos - self.pos if self.pos and max_pos else 0
        print('{}=indent: {} (pos: {}, max_pos:{})'.format(self.line_nr, self.indent, self.pos, max_pos))

class rx:
    heading    = re.compile('^[ \t]*(#)')
    whitespace = re.compile('^[ \t]*$')
    comment    = re.compile('(^[ \t]+)?(?<!\S)(?=#)(?!#\{)')

def get_env(name, default):
    val = os.environ[name] if name in os.environ else default
    if type(default)==int:
        try: val=int(val)
        except: val=default
    return val

class ok_color:
    def __init__(self):
        self.nc      = '\033[0m'
        self.heading = get_env('_OK_C_HEADING', '\033[0;31m')
        self.number  = get_env('_OK_C_NUMBER',  '\033[0;36m')
        self.comment = get_env('_OK_C_COMMENT', '\033[0;34m')
        self.command = get_env('_OK_C_COMMAND', self.nc)
        self.prompt  = get_env('_OK_C_PROMPT',  self.number)

def cprint(color, text=''):
    if color: print(color, end='')
    if text:  print(text, end='')

def parse_lines(lines):
    #handle UTF-8 BOMs: https://stackoverflow.com/a/28407897/56
    if lines[0][:3] == codecs.BOM_UTF8:
        lines[0] = lines[0][3:]
    result = []
    line_nr = 0
    for line in lines:
        line = line.strip('\n')
        heading_match=rx.heading.search(line)
        if heading_match:
            result.append(ParsedLine('heading', line, pos=heading_match.start(1)))
        elif rx.whitespace.search(line):
            result.append(ParsedLine('whitespace', line))
        else:
            line_nr += 1
            match = rx.comment.search(line)
            pos = match.start() if match else None
            result.append(ParsedLine('code', line, line_nr=line_nr, pos=pos))
    return result

def set_indent(l, start, stop, max_pos):
    for i in range(start, stop):
        item = l[i]
        if item.t == 'code':
            item.set_indent(max_pos)

def format_lines(l, elastic_tab, pad_comments, nr_positions_line_nr, max_width):
    if elastic_tab == 0: return
    if elastic_tab == 1: group_reset = ['heading','whitespace']
    if elastic_tab == 2: group_reset = ['heading']
    if elastic_tab == 3: group_reset = []
    start_group = None
    for i in range(0, len(l)):
        x = l[i]
        if start_group is None and x.t not in group_reset:
            start_group = i
            max_pos = x.pos
        if start_group is not None: # We are in a group
            if x.t == 'code':
                max_pos = max(max_pos, x.pos)
            has_no_next_item = i+1>=len(l)
            if has_no_next_item or l[i+1].t in group_reset:
                set_indent(l, start_group, i+1, max_pos)
                start_group = None #reset start code-block
    for i in range(0, len(l)):
        x = l[i]
        if pad_comments == 2 and x.t in ['code', 'heading']:
            pad_value = max_width
            if x.t == 'code':
                pad_value = max_width - nr_positions_line_nr - 2
            x.rpad_to(pad_value, nr_positions_line_nr)

def print_line(l, clr, nr_positions_line_nr, format_line):
    if l.t == 'heading':
        cprint(clr.heading, l.line)
        cprint(None, ParsedLine.INDENT_CHAR*l.rpad)
        cprint(clr.nc, '\n')
    elif l.t == 'whitespace':
        cprint(clr.nc, l.line+'\n')
    elif l.t == 'code':
        if format_line:
            cprint(clr.number, '{:{}}. '.format(l.line_nr, nr_positions_line_nr))
            if l.pos is None:
                cprint(clr.command, l.line)
            else:
                cprint(clr.command, l.line[:l.pos])
                cprint(None, ParsedLine.INDENT_CHAR*l.indent)
                cprint(clr.comment, l.line[l.pos:])
            cprint(None, ParsedLine.INDENT_CHAR*l.rpad)
            cprint(clr.nc, '\n')
        else:
            print(l.line, file=sys.stderr)

def main():
    # customizations
    clr = ok_color()
    comment_align = get_env('_OK_COMMENT_ALIGN', 1)
    if comment_align<0 or comment_align>3: comment_align=1
    pad_comments = get_env('_OK_PAD_COMMENTS', 1)
    if pad_comments<0 or pad_comments>2: pad_comments=1

    # handle arguments
    parser = argparse.ArgumentParser(description='Show the ok-file colorized (or just one line).')
    parser.add_argument('--verbose', '-v', metavar='V', type=int, default=1, help='0=quiet, 1=normal, 2=verbose. Defaults to 1. ')
    parser.add_argument('--terminal_width', '-t', metavar='TW', type=int, default=230, help='number of columns of the terminal (tput cols) ')
    parser.add_argument('only_line_nr', metavar='N', type=int, nargs='?', help='the line number to show')
    args = parser.parse_args()

    if args.verbose > 1:
        print('comment_align:', comment_align)
        print('pad_comments:', pad_comments)
        print('terminal_width:', args.terminal_width)

    # prepare
    UTF8Reader = codecs.getreader('utf8')
    sys.stdin = UTF8Reader(sys.stdin)
    lines = sys.stdin.readlines()
    p_lines = parse_lines(lines)
    nr_positions_line_nr = len(str(max([pl.line_nr for pl in p_lines if pl.line_nr])))
    format_lines(p_lines, comment_align, pad_comments, nr_positions_line_nr, args.terminal_width)

    # execute
    if args.only_line_nr is None:
        for p_line in p_lines:
            print_line(p_line, clr, nr_positions_line_nr, True)
    else:
        try:
            p_line = next(x for x in p_lines if x.t=='code' and x.line_nr==args.only_line_nr)
        except StopIteration:
            if args.verbose >= 2: print("ERROR: entered line number '{}' does not exist".format(args.only_line_nr))
            sys.exit(1)
        # The formated line is printed to stdout, and the actual line from .ok is printed to stderr
        if args.verbose >= 1: print_line(p_line, clr, nr_positions_line_nr, True)
        print_line(p_line, clr, nr_positions_line_nr, False)


if __name__ == "__main__":
    main()


'''
Parsing of comments is not yet perfect. It's also quite complicated. 
See also:
   http://www.apeth.com/nonblog/stories/textmatebundle.html
   https://github.com/stedolan/jq/wiki/Docs-for-Oniguruma-Regular-Expressions-(RE.txt)

Some notes:
In what parts of a bash-line can a #-sign occur:
    - comment
    - interpolation:
        * $()
        * ``
        * $(())   #but how does this work?
    - variables:
      * $# 
      * ${#xxx}
    - string
      * \#
      * double quoted string: variabele/interpolation
'''