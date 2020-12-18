# -*- coding: utf-8 -*-
# Toxine project: Wrapper for tokenized Wikipedia
#
# Copyright (C) 2019-present by Sergei Ternovykh
# License: BSD, see LICENSE for details
"""
Wrapper to get Russian part of Wikipedia tokenized in CoNLL-U format.
"""

from corpuscula.utils import LOG_FILE, print_progress
from corpuscula.wikipedia_utils import Wikipedia
from toxine.text_preprocessor import TextPreprocessor


class TokenizedWikipedia(Wikipedia):
    """Wrapper for Wikipedia corpus"""

    def articles(self, silent=None):
        """Return tokenized Wikipedia articles in CoNLL-U format"""
        silent = self._silent if silent is None else silent
        tp = TextPreprocessor()

        if not silent:
            print('Process Wikipedia', file=LOG_FILE)
        sent_no, article_no = -1, 0
        for article_no, (id_, title, article) in enumerate(
            super().articles(silent=True)
        ):
            tp.new_doc(doc_id=id_, metadata=[('title', title)])
            tp.new_pars(article, eop=r'\n\n', doc_id=id_)
            tp.do_all(silent=True)
            for sent in tp.save(doc_id=id_):
                sent_no += 1
                if not silent and not sent_no % 100:
                    print_progress(sent_no, end_value=None, step=1000,
                                   file=LOG_FILE)
                yield sent
            tp.remove_doc(id_)
        if not silent and sent_no >= 0:
            sent_no += 1
            print_progress(sent_no, end_value=0, step=1000,
                           file=LOG_FILE)
            print('Wikipedia has been processed: {} sentences, {} articles'
                      .format(sent_no, article_no, file=LOG_FILE))
