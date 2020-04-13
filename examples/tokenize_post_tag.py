#!/usr/bin/python
# -*- coding: utf-8 -*-
# Tuko project: Text Preprocessing pipeline
#
# Copyright (C) 2019-present by Sergei Ternovykh
# License: BSD, see LICENSE for details
"""
Example: tokenize TXT file and expand default set of detecting entities.
"""
import os
import re

from corpuscula.corpus_utils import syntagrus
from tuko import TextPreprocessor


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
##
# The example of ``do_all()`` *post_tag* attribute usage
##
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

cdict_path = os.path.join(SCRIPT_DIR, 'cdict.pickle')
tp = TextPreprocessor(cdict_restore_from=cdict_path) \
         if os.path.isfile(cdict_path) else \
     TextPreprocessor(cdict_corpus=syntagrus, cdict_backup_to=cdict_path)
tp.load_pars(os.path.join(SCRIPT_DIR, 'data.txt'), eop=r'\n')
tp.register_tag(TAG_YEARBIRTH, mask='год рождения')
tp.register_tag(TAG_YEAR, mask='год')
tp.do_all(post_tag=tag_birth_year)
tp.save('data.conllu')
