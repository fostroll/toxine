#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re

###
import sys
sys.path.append('../')
###

from tests._test_support import WORK_DIR, WORK_FNAME, \
                                bprint, eprint, safe_run, check_res
#from corpuscula.corpus_utils import syntagrus
from toxic import TextPreprocessor

WORK_FNAME = os.path.join(WORK_DIR, 'test$')

def filecmp(fpath1, fpath2):
    res = True
    with open(fpath1, 'rt', encoding='utf-8-sig') as f1, \
         open(fpath2, 'rt', encoding='utf-8-sig') as f2:
        for line1 in f1:
            line2 = next(f2)
            if (line1 or line2) and line1[0] == '#':
                i = line1.index('=')
                if line1[:i] != line2[:i]:
                    print(line1)
                    print(line2)
                    res = False
                    break
            elif line1 != line2:
                print(line1)
                print(line2)
                res = False
                break
        try:
            next(f2)
        except StopIteration:
            pass
        else:
            res = False
    return res

def f ():
    TAG_YEARBIRTH = 'EntityYearOfBirth'
    TAG_YEAR = 'EntityYear'

    def tag_birth_year (text, delim):
        def process (match):
            y, isbirth = int(match.group(1)), match.group(2)
            return ' {}{}{} '.format(y, delim, TAG_YEARBIRTH if isbirth else
                                               TAG_YEAR) \
                       if y > 1900 and y < 2030 else \
                   match.group(0)
        text = re.sub(
            r'\b(\d{4})\s*?(?:(?:(г(?:\.|\s|$)))|год(?:а|у|\.|\s|$))\s*'
                             '((?:р(?:\.|\s|$))|(?:рожд(?:\.|\s|$)))?',
            process, text
        )
        return text

    cdict_path = os.path.join(WORK_DIR, 'cdict.pickle')
    tp = TextPreprocessor()
    tp.load_pars(os.path.join(WORK_DIR, 'test.txt'), eop=r'\n')
    tp.register_tag(TAG_YEARBIRTH, mask='год рождения')
    tp.register_tag(TAG_YEAR, mask='год')
    tp.do_all(post_tag=tag_birth_year)
    tp.save(WORK_FNAME, add_global_columns=True)
    return filecmp(WORK_FNAME, os.path.join(WORK_DIR, 'test3.conllu'))
check_res(safe_run(f, 'Tesing TextPreprocessor'))

os.remove(WORK_FNAME)
