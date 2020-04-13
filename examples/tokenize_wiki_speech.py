#!/usr/bin/python
# -*- coding: utf-8 -*-
# Tuko project: Text Preprocessing pipeline
#
# Copyright (C) 2019-present by Sergei Ternovykh
# License: BSD, see LICENSE for details
"""
Example: Tokenize Wikipedia and make its articles looks like some speech
recognition software output. Save the result as CONLL-U.
"""
from corpuscula import Conllu
from corpuscula.wikipedia_utils import download_wikipedia
from tuko.wikipedia_utils import TokenizedWikipedia

download_wikipedia(overwrite=False)
Conllu.save(TokenizedWikipedia().articles(), 'wiki_speech.conllu', fix=True,
            adjust_for_speech=True, log_file=None)
