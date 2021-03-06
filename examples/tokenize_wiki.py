#!/usr/bin/python
# -*- coding: utf-8 -*-
# Toxine project
#
# Copyright (C) 2019-present by Sergei Ternovykh
# License: BSD, see LICENSE for details
"""
Example: Tokenize Wikipedia and save articles as CoNLL-U.
"""
from corpuscula import Conllu
from corpuscula.wikipedia_utils import download_wikipedia
from toxine.wikipedia_utils import TokenizedWikipedia


# download syntagrus if it's not done yet
download_wikipedia(overwrite=False)
# tokenize and save articles
Conllu.save(TokenizedWikipedia().articles(), 'wiki.conllu', fix=False,
            log_file=None)
