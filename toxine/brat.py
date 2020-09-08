# -*- coding: utf-8 -*-
# Toxine project: converters for brat format
#
# Copyright (C) 2019-present by Sergei Ternovykh
# License: BSD, see LICENSE for details
"""
Provides tools for convertation brat text bound annotations
"""
from corpuscula import Conllu
import re
from toxine import TextPreprocessor
import warnings

BRAT_TEXT_BOUND_START_MARKS = '[T>>', ']'
BRAT_TEXT_BOUND_END_MARKS = '[', '<<T]'
TAGS_BRAT = 'BratTStart', 'BratTEnd'
TAG_BRAT = 'Brat'
TAG_NE = 'NE'


def add_brat_text_bound_annotations(txt_fn, ann_fn, save_to=None):
    """
    """
    def process():
        anns = []
        with open(ann_fn, 'rt', encoding='utf=8') as f:
            for i, ann in enumerate(f, start=1):
                id_, type_ = (ann.strip().split('\t') + [''])[:2]
                if id_ and type_:
                    if id_[0] == 'T':
                        type_ = type_.split()
                        if len(type_) == 3:
                            type_, start, end = type_
                            try:
                                start, end = int(start), int(end)
                            except ValueError:
                                raise ValueError(
                                    'ERROR: Invalid position number in line '
                                    '{}'.format(i)
                                )
                            anns.append((start, -end, i, type_))
                            anns.append((end, -start, -i, type_))
        anns.sort()

        done_len = 0
        ianns = iter(anns)
        ann = next(ianns, None)
        with open(txt_fn, 'rt', encoding='utf-8') as f_in:

            for line in f_in:
                if line[-1] != '\n':
                    line += '\n'
                line_ = ''
                while ann and ann[0] < done_len + len(line):
                    pos, _, start_flag, type_ = ann
                    pos_ = pos - done_len

                    if pos_ > 0:
                        if start_flag > 0:
                            ne_chr = line[pos_]
                            ne_type = 2 if ne_chr.isalpha() else \
                                      1 if ne_chr.isdigit() else \
                                      0
                            while pos_ > 0:
                                if (ne_type == 2 and line[pos_ - 1]
                                                         .isalpha()) \
                                or (ne_type == 1 and line[pos_ - 1]
                                                         .isdigit()):
                                    pos_ -= 1
                                else:
                                    break
                        else:
                            ne_chr = line[pos_ - 1]
                            ne_type = 2 if ne_chr.isalpha() else \
                                      1 if ne_chr.isdigit() else \
                                      0
                            line_len = len(line)
                            while pos_ < line_len:
                                if (ne_type == 2 and line[pos_].isalpha()) \
                                or (ne_type == 1 and line[pos_].isdigit()):
                                    pos_ += 1
                                else:
                                    break

                    line_ += line[:pos_]
                    line = line[pos_:]
                    done_len += pos_

                    mark = BRAT_TEXT_BOUND_START_MARKS \
                               if start_flag > 0 else \
                           BRAT_TEXT_BOUND_END_MARKS
                    sp = ('', '')
                    #sp = ('' if not line_ or line_[-1].isspace() else ' ',
                    #      '' if line[0].isspace() else ' ')
                    line_ += sp[0] + mark[0] + type_ + mark[1] + sp[1]
                    ann = next(ianns, None)
                yield line_ + line.rstrip()
                done_len += len(line)

    res = process()
    if save_to:
        with open(save_to, 'wt', encoding='utf-8') as f:
            for line in res:
                print(line, file=f)
    else:
        return res

def postprocess_brat_conllu(corpus, save_to=None):
    """
    """
    def process():
        for sent, meta in Conllu.load(corpus) \
                              if isinstance(corpus, str) else \
                          corpus:
            meta.pop('text', None)
            sent_ = []
            tags = []
            for token in sent:
                misc = token['MISC']
                if token['FORM'] is None:
                    if TAGS_BRAT[0] in misc:
                        if TAGS_BRAT[0] not in tags:
                            tags.append(misc[TAGS_BRAT[0]])
                    elif TAGS_BRAT[1] in misc:
                        try:
                            tags.remove(misc[TAGS_BRAT[1]])
                        except:
                            pass
                        if sent_ and 'SpaceAfter' in misc:
                            sent_[-1]['MISC']['SpaceAfter'] = misc['SpaceAfter']
                    else:
                        sent_.append(token)
                else:
                    for tag in tags:
                        misc[TAG_BRAT + tag] = 'Yes'
                    sent_.append(token)
            yield sent_, meta

    res = process()
    if save_to:
        Conllu.save(res, save_to, fix=True)
    else:
        return Conllu.fix(res)

def make_ne_tags(corpus, save_to=None):
    """
    """
    def process():
        for i, (sent, meta) in enumerate(
            Conllu.load(corpus) if isinstance(corpus, str) else corpus
        ):
            tag_brat_len = len(TAG_BRAT)
            for token in sent:
                misc = token['MISC']
                ne = None
                ne_excess = set()
                for feat, val in misc.items():
                    if feat.startswith(TAG_BRAT) and val == 'Yes':
                        if ne:
                            warnings.warn(
                                'Multiple brat entities in sent '
                                '{} (sent_id = {}), token {} ("{}"):'
                                    .format(i, meta['sent_id'],
                                            token['ID'], token['FORM'])
                              + ': Entities {} and {}. Ignore the last one'
                                    .format(ne, feat))
                            ne_excess.add(feat)
                        else:
                            ne = feat
                if ne:
                    for ne_ in [ne] + list(ne_excess):
                        misc.pop(ne_)
                    misc[TAG_NE] = ne[tag_brat_len:]
            yield sent, meta

    res = process()
    if save_to:
        Conllu.save(res, save_to, fix=False)
    else:
        return res

def brat_to_ne(txt_fn, ann_fn, save_to=None):
    """
    """
    def tag_brat_text_bound_annotation(text, delim):
        def process(match):
            tag_start, tag_end = match.group(1), match.group(2)
            return ' {}{}{} '.format(tag_start or tag_end, delim,
                                     TAGS_BRAT[0] if tag_start else TAGS_BRAT[1])
        text = re.sub(
            BRAT_TEXT_BOUND_START_MARKS[0].replace('[', r'\[') + r'(\S+?)'
          + BRAT_TEXT_BOUND_START_MARKS[1]
          + '|'
          + BRAT_TEXT_BOUND_END_MARKS[0].replace('[', r'\[') + r'(\S+?)'
          + BRAT_TEXT_BOUND_END_MARKS[1],
            process, text
        )
        return text

    sents = add_brat_text_bound_annotations(txt_fn, ann_fn)
    tp = TextPreprocessor()
    for sent in sents:
        tp.new_par(sent)
    tp.register_tag(TAGS_BRAT[0])
    tp.register_tag(TAGS_BRAT[1])
    tp.do_all(post_tag=tag_brat_text_bound_annotation)
    return make_ne_tags(postprocess_brat_conllu(tp.save()), save_to=save_to)


brat_to_ne('03_Test.txt', '03_Test.ann', 'data.conllu')
