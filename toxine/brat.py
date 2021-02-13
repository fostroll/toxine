# -*- coding: utf-8 -*-
# Toxine project: converters for brat format
#
# Copyright (C) 2019-present by Sergei Ternovykh
# License: BSD, see LICENSE for details
"""
Provides tools for convertation brat text-bound annotations.
"""
from corpuscula import Conllu
import glob
import io
import os
import re
from toxine import TextPreprocessor
import warnings

BRAT_TEXT_BOUND_START_MARK, BRAT_TEXT_BOUND_END_MARK = '[{}>>]', '[<<{}]'
BRAT_START_TAG, BRAT_END_TAG = 'bratTStart', 'bratTEnd'
BRAT_TAG = 'brat'
TAG_NE = 'NE'
SEP1, SEP2, SEP3 = '!', '/', ':'

RE_BRAT = re.compile((BRAT_TEXT_BOUND_START_MARK.format(r'(\S+?)') + '|'
                    + BRAT_TEXT_BOUND_END_MARK.format(r'(\S+?)'))
                         .replace('[', r'\['))


def embed_brat_annotations(txt_fn, ann_fn, save_to=None, keep_tokens=True):
    """Converts txt and ann files generated by brat to the text file with
    embedded annotations.

    :param txt_fn: a path to the brat txt file.
    :param ann_fn: a path to the brat ann file.
    :param save_to: a path where result will be stored. If ``None`` (default),
                    the function returns the result as a generator of text
                    data.
    :param keep_tokens: if ``True`` (default), the function adjusts borders
                        of annotations to the borders of text tokens. If
                        ``False``, the borders are left as is, so some tokens
                        may be splitted.
    """
    def process_entity(text):
        text = text.split('\t')
        assert len(text) == 3
        tid, ann, _ = text
        ann = ann.split(' ', maxsplit=1)
        assert len(ann) == 2
        name, offs = ann
        offs = offs.split(';')
        offsets = []
        for off in offs:
            off = tuple(off.split())  # (start, stop)
            assert len(off) == 2
            offsets.append(off)
        return 'T', tid, name, *offsets

    def process_relation(text):
        text = text.split('\t')
        assert len(text) == 2
        rid, ann = text
        ann = ann.split()
        assert len(ann) == 3
        name, args = ann[0], ann[1:]
        arguments = []
        for arg in args:
            arg = tuple(arg.split(':'))  # (role, tid)
            assert len(arg) == 2
            arguments.append(arg)
        return 'R', rid, name, *arguments

    def process_equivalence(text):
        text = text.split('\t')
        assert len(text) == 2 and text[0] == '*'
        return '*', '*', *text[1].split()  # (name, tid, ...)

    def process_event(text):
        text = text.split('\t')
        assert len(text) == 2
        eid, ann = text
        ann = ann.split()
        assert len(ann) >= 2
        arguments = []
        for arg in ann:
            arg = tuple(arg.split(':'))  # (name, tid) | (role, tid)
            assert len(arg) == 2
            arguments.append(arg)
        return 'E', eid, *arguments

    def process_attribute(text):
        text = text.split('\t')
        assert len(text) == 2
        aid, ann = text
        ann = ann.split() + ['']  # [name, tid, value]
        assert len(ann) in [3, 4]
        return 'A', aid, *ann[:3]

    def process_normalization(text):
        text = text.split('\t')
        assert len(text) == 3
        nid, ann, title = text
        ann = ann.split()
        assert len(ann) == 3
        name, tid, src = ann
        assert name == 'Reference'
        src = src.split(':')  # [service_name, service_id]
        assert len(src) == 2
        return 'N', nid, title, tid, *src

    def process_note(text):
        text = text.split('\t')
        assert len(text) == 3
        nid, ann, note = text
        ann = ann.split()
        assert len(ann) == 2
        name, tid = ann
        assert name == 'AnnotatorNotes'
        return '#', nid, note, tid

    def process():
        anns = {}
        with open(ann_fn, 'rt', encoding='utf=8') as f:
            qid = 1
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                try:
                    res = process_entity(line) \
                              if line.startswith('T') else \
                          process_relation(line) \
                              if line.startswith('R') else \
                          process_equivalence(line) \
                              if line.startswith('*') else \
                          process_event(line) \
                              if line.startswith('E') else \
                          process_attribute(line) \
                              if line.startswith('A') \
                              or line.startswith('M') else \
                          process_normalization(line) \
                              if line.startswith('N') else \
                          process_note(line) \
                              if line.startswith('#') else \
                          None
                    assert res
                    ann_type, ann_id = res[:2]
                    anns_t = anns.setdefault(ann_type, {})
                    if ann_type == '*':
                        ann_id = ann_id + str(qid)
                        qid += 1
                    assert ann_id not in anns_t
                    anns_t[ann_id] = res[2:] + (line_no,)
                except AssertionError:
                    raise ValueError('ERROR: Invalid annotation '
                                     'in line {})'.format(line_no))

        entities = []
        relations, equivalences, events, attributes, normalizations, notes = \
            {}, {}, {}, {}, {}, {}
        for ann_type, ann in anns.items():
            for ann_id, entity in ann.items():
                name, line_no = entity[0], entity[-1]

                def check_availability(ann_id):
                    for _, ann in anns.items():
                        if ann_id in ann:
                            break
                    else:
                        raise ValueError('ERROR: Unknown annotation id ({}) '
                                         'in line {}'.format(ann_id, line_no))

                if ann_type == 'T':
                    for start, end in entity[1:-1]:
                        try:
                            start, end = int(start), int(end)
                        except ValueError:
                            raise ValueError('ERROR: Invalid offset in line '
                                             '{}'.format(line_no))
                        entities.append((start, -end, line_no, name, ann_id))
                        entities.append((end, -start, -line_no, name, ann_id))
                elif ann_type == 'R':
                    for role, tid in entity[1:-1]:
                        check_availability(tid)
                        anns_t = relations.setdefault(tid, [])
                        anns_t.append((ann_id, name, role))
                elif ann_type == '*':
                    for tid in entity[1:-1]:
                        check_availability(tid)
                        anns_t = equivalences.setdefault(tid, [])
                        anns_t.append((ann_id, name))
                elif ann_type == 'E':
                    name, tid = name
                    for role, tid in (('', tid),) + entity[1:-1]:
                        check_availability(tid)
                        anns_t = events.setdefault(tid, [])
                        anns_t.append((ann_id, name, role))
                elif ann_type == 'A':
                    tid, value = entity[1:-1]
                    check_availability(tid)
                    anns_t = attributes.setdefault(tid, [])
                    anns_t.append((ann_id, name, value))
                elif ann_type == 'N':
                    tid, service_name, service_id = entity[1:-1]
                    check_availability(tid)
                    anns_t = normalizations.setdefault(tid, [])
                    anns_t.append((ann_id, service_name, service_id, name))
                elif ann_type == '#':
                    tid, = entity[1:-1]
                    check_availability(tid)
                    anns_t = notes.setdefault(tid, [])
                    anns_t.append((ann_id, name))
        entities.sort()

        done_len = 0
        ientities = iter(entities)
        entity = next(ientities, None)
        with io.open(txt_fn, 'rt', encoding='utf-8', newline='') as f_in:

            for line in f_in:
                if line[-1] != '\n':
                    line += '\n'
                line_ = ''
                while entity and entity[0] < done_len + len(line):
                    pos, _, start_flag, name, tid = entity
                    ann_text = '{}{}{}'.format(tid, SEP2, name)
                    pos_ = pos - done_len

                    if keep_tokens:
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
                                    if (ne_type == 2 and line[pos_]
                                                             .isalpha()) \
                                    or (ne_type == 1 and line[pos_]
                                                             .isdigit()):
                                        pos_ += 1
                                    else:
                                        break

                    line_ += line[:pos_]
                    line = line[pos_:]
                    done_len += pos_

                    if start_flag > 0:
                        mark = BRAT_TEXT_BOUND_START_MARK

                        def mask(text):
                            return text.replace(mark[-1],
                                                r'\{}'.format(mark[-1])) \
                                       .replace(SEP1, r'\{}'.format(SEP1)) \
                                       .replace('_', r'\_').replace(' ', '__')

                        ann_text_ = ''
                        for ann_id, name, role in relations.get(tid, []):
                            ann_text_ += '{}{}{}{}{}{}{}'.format(
                               SEP1, ann_id, SEP2, name, SEP2, role, SEP1
                            )
                        for ann_id, name in equivalences.get(tid, []):
                            ann_text_ += '{}{}{}{}{}'.format(
                                SEP1, ann_id, SEP2, name, SEP1
                            )
                        for ann_id, name, role in events.get(tid, []):
                            ann_text_ += '{}{}{}{}{}{}{}'.format(
                                SEP1, ann_id, SEP2, name, SEP2, role, SEP1
                            )
                        for ann_id, name, value in attributes.get(tid, []):
                            ann_text_ += '{}{}{}{}{}{}{}'.format(
                                SEP1, ann_id, SEP2, name, SEP2, value, SEP1
                            )
                        for ann_id, service_name, service_id, title in \
                            normalizations.get(tid, []):
                            ann_text_ += '{}{}{}{}{}{}{}{}{}'.format(
                                SEP1, ann_id, SEP2, service_name,
                                SEP2, service_id, SEP2, mask(title), SEP1)
                        for ann_id, name in notes.get(tid, []):
                            ann_text_ += '{}{}{}{}{}'.format(
                                SEP1, ann_id, SEP2, mask(name), SEP1
                            )
                        if ann_text_:
                            ann_text += SEP1 + ann_text_[:-1]
                    else:
                        mark = BRAT_TEXT_BOUND_END_MARK
                        ann_text = tid
                    sp = ('', '')
                    #sp = ('' if not line_ or line_[-1].isspace() else ' ',
                    #      '' if line[0].isspace() else ' ')
                    line_ += sp[0] + mark.format(ann_text) + sp[1]
                    entity = next(ientities, None)
                yield line_ + line.rstrip()
                done_len += len(line)

    res = process()
    if save_to:
        with io.open(save_to, 'wt', encoding='utf-8', newline='\n') as f:
            for line in res:
                print(line, file=f)
    else:
        return res

def postprocess_brat_conllu(corpus, save_to=None):
    """Does postprocessing for the *corpus* with embedded brat annotations
    which already was preliminarily prepared by Toxine's TextPreprocessor.

    :param corpus: corpus in Parsed CoNLL-U format or a path to the previously
                   saved corpus in CoNLL-U format.
    :param save_to: a path where result will be stored. If ``None`` (default),
                    the function returns the result as a generator of Parsed
                    CoNLL-U data.
    """
    def process():

        def unmask(text):
            return text.replace(r'\{}'.format(BRAT_TEXT_BOUND_START_MARK[-1]),
                                BRAT_TEXT_BOUND_START_MARK[-1]) \
                       .replace(r'\{}'.format(SEP1), SEP1) \
                       .replace('__', ' ').replace(r'\_', '_')

        for sent, meta in Conllu.load(corpus) \
                              if isinstance(corpus, str) else \
                          corpus:
            meta.pop('text', None)
            if 'par_text' in meta:
                meta['par_text'] = RE_BRAT.sub('', meta['par_text'])
            sent_ = []
            anns = []
            for token in sent:
                misc = token['MISC']
                if token['FORM'] is None:
                    if BRAT_START_TAG in misc:
                        assert BRAT_START_TAG not in anns
                        assert misc[BRAT_START_TAG][0] == 'T'
                        anns.append(misc[BRAT_START_TAG])
                    elif BRAT_END_TAG in misc:
                        anns_ = []
                        for ann in anns:
                            prefix = misc[BRAT_END_TAG] + SEP2
                            anns = list(filter(
                                lambda x: not x.startswith(prefix), anns
                            ))
                        try:
                            tags.remove(misc[BRAT_END_TAG])
                        except:
                            pass
                        if sent_ and 'SpaceAfter' in misc:
                            sent_[-1]['MISC']['SpaceAfter'] = \
                                misc['SpaceAfter']
                    else:
                        sent_.append(token)
                else:
                    for ann in anns:
                        ann = ann.split(SEP1 + SEP1)
                        entity, ann_ = ann[0], ann[1:]
                        tid, name = entity.split(SEP2)
                        assert tid.startswith('T'), \
                            'ERROR: Unrecognized annotation {}'.format(ann)
                        misc[BRAT_TAG + tid] = name
                        for ann in ann_:
                            if ann.startswith('R'):
                                ann_id, name, role = ann.split(SEP2)
                                misc[BRAT_TAG + ann_id] = \
                                    tid + SEP3 + name + SEP3 + role
                            elif ann.startswith('*'):
                                ann_id, name = ann.split(SEP2)
                                misc[BRAT_TAG + ann_id] = tid + SEP3 + name
                            elif ann.startswith('E'):
                                ann_id, name, role = ann.split(SEP2)
                                val = tid + SEP3 + name
                                if role:
                                    val += SEP3 + role
                                misc[BRAT_TAG + ann_id] = val
                            elif ann.startswith('A'):
                                ann_id, name, value = ann.split(SEP2)
                                val = tid + SEP3 + name
                                if value:
                                    val += SEP3 + value
                                misc[BRAT_TAG + ann_id] = val
                            elif ann.startswith('N'):
                                ann_id, service_name, service_id, title = \
                                    ann.split(SEP2, maxsplit=3)
                                misc[BRAT_TAG + ann_id] = \
                                    tid + SEP3 + service_name \
                                  + SEP3 + service_id + SEP3 + unmask(title)
                            elif ann.startswith('#'):
                                ann_id, note = ann.split(SEP2, maxsplit=1)
                                misc[BRAT_TAG + ann_id] = \
                                    tid + SEP3 + unmask(note)
                            else:
                                raise ValueError('ERROR: Unknown annotation '
                                                 'type')
                        #misc[BRAT_TAG + ann] = 'Yes'
                    sent_.append(token)
            yield sent_, meta

    res = process()
    if save_to:
        Conllu.save(res, save_to, fix=True)
    else:
        return Conllu.fix(res)

def make_ne_tags(corpus, save_to=None, keep_originals=True):
    """Process the *corpus* in CoNLL-U or Parsed CoNLL-U format such that
    MISC:bratT entities converts to MISC:NE entities supported by MorDL. Note,
    that if several bratT entities are linked to the one token, only first one
    will be used (it is allowed only one MISC:NE entity for the token).

    :param corpus: corpus in Parsed CoNLL-U format or a path to the previously
                   saved corpus in CoNLL-U format.
    :param save_to: a path where result will be stored. If ``None`` (default),
                    the function returns the result as a generator of Parsed
                    CoNLL-U data.
    :param keep_originals: If ``True`` (default), original MISC:bratT entities
                           will be stayed intact. Elsewise, they will be
                           removed.
    """
    TAG = BRAT_TAG + 'T'

    def process():
        for i, (sent, meta) in enumerate(
            Conllu.load(corpus) if isinstance(corpus, str) else corpus
        ):
            for token in sent:
                misc = token['MISC']
                ne = None
                ne_excess = set()
                for feat, val in misc.items():
                    if feat.startswith(TAG):
                        if ne and ne != val:
                            warnings.warn(
                                'Multiple brat entities in sent '
                                '{} (sent_id = {}), token {} ("{}"):'
                                    .format(i, meta['sent_id'],
                                            token['ID'], token['FORM'])
                              + ': Entities {} and {}. Ignore the last one'
                                    .format(ne, val))
                        else:
                            ne = val
                        ne_excess.add(feat)
                if ne:
                    if not keep_originals:
                        for ne_ in list(ne_excess):
                            misc.pop(ne_)
                    misc[TAG_NE] = ne
            yield sent, meta

    res = process()
    if save_to:
        Conllu.save(res, save_to, fix=False)
    else:
        return res

def brat_to_conllu(txt_fn, ann_fn=None, save_to=None, keep_tokens=True,
                   make_ne=False, keep_originals=True, cdict_path=None,
                   **kwargs):
    """Converts txt and ann files generated by brat to CoNLL-U file with brat
    annotations placed to the MISC:brat fields.

    :param txt_fn: a path to the brat txt file.
    :param ann_fn: a path to the brat ann file. If ``None`` (default), an
                   extension of *txt_fn* file will be changed to '.ann'.
    :param save_to: a path where result will be stored. If ``None`` (default),
                    the function returns the result as a generator of Parsed
                    CoNLL-U data.
    :param keep_tokens: if ``True`` (default), the function adjusts borders
                        of annotations to the borders of text tokens. If
                        ``False``, the borders are left as is, so some tokens
                        may be splitted.
    :param make_ne: if ``True``, brat "T" entities will convert to MISC:NE
                    entities supported by MorDL. Note, that if several brat
                    "T" entities are linked to the one token, only first one
                    will be used (it is allowed only one MISC:NE entity for
                    the token). Default ``False``.
    :param keep_originals: relevant with make_ne = ``True``. If keep_originals
                           is ``True`` (default), original MISC:bratT entities
                           will be stayed intact. Elsewise, they will be
                           removed.
    :param cdict_path: (optional) a path to the `corpuscula.corpus_dict`
                       backup file.
    Also, the function receives other parameters that fit for Toxine's
    ``TextPreprocessor.do_all()`` method."""
    fn, fe = os.path.splitext(txt_fn)
    if fe != '.txt':
        print('WARNING: Extension of txt_fn must be ".txt"', file=sys.stderr)
    if ann_fn is None:
        ann_fn = fn + '.ann'
    _, fe = os.path.splitext(ann_fn)
    if fe != '.ann':
        print('WARNING: Extension of ann_fn must be ".ann"', file=sys.stderr)

    def tag_brat_annotations(text, delim):
        def process(match):
            tag_start, tag_end = match.group(1), match.group(2)
            return ' {}{}{} ' \
                       .format(tag_start or tag_end, delim,
                               BRAT_START_TAG if tag_start else BRAT_END_TAG)
        #'\[(?P<ID>T\d+)>>](.+?)\[<<(?P=ID)]'
        text = RE_BRAT.sub(process, text)
        return text

    sents = embed_brat_annotations(txt_fn, ann_fn, keep_tokens=keep_tokens)
    tp = TextPreprocessor(cdict_restore_from=cdict_path)
    for sent in sents:
        tp.new_par(sent)
    tp.register_tag(BRAT_START_TAG)
    tp.register_tag(BRAT_END_TAG)

    kwargs['post_tag'] = \
        (lambda text, delim: \
             kwargs['post_tag'](tag_brat_annotations(text, delim))) \
            if 'post_tag' in kwargs else \
        tag_brat_annotations
    kwargs['is_tokenized'] = True

    tp.do_all(**kwargs)
    return make_ne_tags(postprocess_brat_conllu(tp.save()), save_to=save_to,
                        keep_originals=keep_originals) \
               if make_ne else \
           postprocess_brat_conllu(tp.save(), save_to=save_to)

def conllu_to_brat(corpus, txt_fn, ann_fn=None, spaces=1):
    """Converts *corpus* in CoNLL-U format to txt and ann files used by brat.

    :param txt_fn: a path to the brat txt file.
    :param ann_fn: a path to the brat ann file. If ``None`` (default), an
                   extension of *txt_fn* file will be changed to '.ann'.
    :param save_to: a path where result will be stored. If ``None`` (default),
                    the function returns the result as a generator of Parsed
                    CoNLL-U data.
    :param spaces: number of spaces to use as word delimiter.

    Note, that we create empty `.ann` files. Use this function to get initial
    data for annotation."""
    fn, fe = os.path.splitext(txt_fn)
    if fe != '.txt':
        print('WARNING: Extension of txt_fn must be ".txt"', file=sys.stderr)
    if ann_fn is None:
        ann_fn = fn + '.ann'
    _, fe = os.path.splitext(ann_fn)
    if fe != '.ann':
        print('WARNING: Extension of ann_fn must be ".ann"', file=sys.stderr)

    with io.open(txt_fn, 'wt', encoding='utf-8', newline='\n') as out_f, \
         open(ann_fn, 'w'):
        for sent_no, sent in enumerate(Conllu.load(corpus, fix=False,
                                                   log_file=None)):
            if sent_no:
                print(file=out_f)
                if 'newpar id' in sent[1]:
                    print(file=out_f)
            for tok_no, tok in enumerate(sent[0]):
                if tok_no:
                    print(' ' * spaces, end='', file=out_f)
                form, misc = tok['FORM'], tok['MISC']
                has_entity = False
                for feat, value in misc.items():
                    if feat.startswith('Entity'):
                        assert not has_entity
                        form = value
                        has_entity = True
                print(form, end='', file=out_f)

def renew_ann(old_txt_fn, old_ann_fn, new_txt_fn, save_new_ann_to,
              rewrite=False):
    """If we have a brat annotation for some txt-file already done, and we
    have to change that txt slightly, this method helps you to adjust the
    annotation for new version of the txt.

    :param old_txt_fn: a path to the old txt-file.
    :param old_ann_fn: a path to the old ann-file.
    :param new_txt_fn: a path to the new txt-file.
    :param save_new_ann_to: a path where the renewed ann will be saved to.
    :param rewrite: if ``True``, allow *save_new_ann_to* be equal to
                    *old_ann_fn*. Default is ``False``.
    """
    assert rewrite or save_new_ann_to != old_ann_fn, \
        'ERROR: use `rewrite=True` param if you really want to change ' \
        'original ann-file'

    from Levenshtein import editops

    with io.open(old_txt_fn, 'rt', encoding='utf-8', newline='') as f:
        old_txt = f.read()
    with io.open(new_txt_fn, 'rt', encoding='utf-8', newline='') as f:
        new_txt = f.read()
        if '\r' in new_txt:
            print('WARNING: The new txt file ("{}") file contain "CR" '
                  'symbols that may cause errors ("nonprintable characters") '
                  'in brat engine. Consider to remove "CR" symbols from new '
                  'txt file and renew annotations again'.format(new_txt_fn))
    with open(old_ann_fn, 'rt', encoding='utf-8') as f:
        old_ann = f.read().split('\n')
    transfer_map, shift, prev_idx = list(range(len(old_txt) + 1)), 0, 0
    for op, idx_src, idx_dst in editops(old_txt, new_txt):
        if shift:
            for idx in range(prev_idx, idx_src):
                transfer_map[idx] += shift
        if op == 'insert':
            shift += 1
            prev_idx = idx_src
        elif op == 'replace':
            transfer_map[idx_src] += shift
            prev_idx = idx_src + 1
        elif op == 'delete':
            transfer_map[idx_src] = None
            shift -= 1
            prev_idx = idx_src + 1
        else:
            raise ValueError('ERROR: Unknown operation "{}"'.format(op))
    if shift:
        for idx in range(prev_idx, len(old_txt) + 1):
            transfer_map[idx] += shift
    new_ann = []
    len_old_txt, len_new_txt = len(old_txt), len(new_txt)
    old_aids, new_aids, aid_map, all_spans = set(), set(), {}, {}
    for line_no, ann in enumerate(old_ann, start=1):
        ann = ann.split('\t')
        if not ann:
            continue
        aid = ann[0]
        old_aids.add(aid)
        chunks_old = ann[1].split(';') if len(ann) >= 2 else []
        chunks_new, spans, fragments = [], [], []
        for chunk_old in chunks_old:
            chunk_new, span, idx0 = [], [], None
            for token in chunk_old.split():
                if token.isdigit():
                    idx_ = int(token)
                    assert idx_ <= len_old_txt, \
                        'ERROR: Position "{}" in line {} is outside of ' \
                        'bounds of the file {}' \
                            .format(idx_, line_no, old_ann_fn)
                    # if we have a start of the fragment
                    if not span:
                        # search for transfer not to None
                        for idx in transfer_map[idx_:]:
                            if idx is not None:
                                idx0 = idx
                                if idx == len_new_txt:
                                    idx = None
                                else:
                                    # if the old fragment starts after ' ',
                                    # the new one should do, too
                                    if idx_ == 0 \
                                    or old_txt[idx_ - 1].isspace():
                                        for i in range(idx, 0, -1):
                                            if new_txt[i - 1].isspace():
                                                idx = i
                                                break
                                        else:
                                            idx = 0
                                    # anyway, we can't point to ' '
                                    for i in range(idx, len_new_txt):
                                        if not new_txt[i].isspace():
                                            idx = i
                                            break
                                    else:
                                        idx = None
                                    #idx0 = idx
                                if idx is None:
                                    token = None
                                else:
                                    span.append(idx)
                                    token = str(idx)
                                break
                        else:
                            break
                    # end of the fragment
                    else:
                        for idx in reversed(transfer_map[:idx_ + 1]):
                            if idx is not None:
                                if idx <= idx0:
                                    idx = span = None
                                else:
                                    # if the old fragment ends with ' ',
                                    # the new one should do, too
                                    if idx_ == len_old_txt \
                                    or old_txt[idx_].isspace():
                                        for i in range(idx, len_new_txt):
                                            if new_txt[i].isspace():
                                                idx = i
                                                break
                                        else:
                                            idx = len_new_txt
                                    # anyway, we don't want to have ' '
                                    # in the end
                                    for i in range(idx, 0, -1):
                                        if not new_txt[i - 1].isspace():
                                            idx = i
                                            break
                                    else:
                                        idx = None
                                if idx is None:
                                    token = None
                                else:
                                    span.append(idx)
                                    token = str(idx)
                                break
                        else:
                            break
                if token is None or (token in old_aids
                                 and token not in new_aids):
                    token = aid_map.get(token)
                    if not token:
                        chunk_new = None
                        break
                chunk_new.append(token)
            if span:
                if len(span) != 2:
                    print(span)
                assert len(span) == 2, 'ERROR: Invalid line {} in {} file' \
                                           .format(line_no, old_ann_fn)
                for span_ in spans:
                    if span[0] >= span_[0] and span[0] < span_[1]:
                        span[0] = span_[1]
                    if span[1] > span_[0] and span[1] <= span_[1]:
                        span[1] = span_[0]
                if span[1] > span[0]:
                    for i, span_ in enumerate(reversed(spans), start=1):
                        if span[0] == span_[1]:
                            span_[1] = span[1]
                        elif span[1] == span_[0]:
                            span_[0] = span[0]
                        else:
                            continue
                        chunks_new[-i][-2:] = [str(span_[0]), str(span_[1])]
                        fragments[-i] = new_txt[span_[0]:span_[1]]
                        chunk_new = None
                        break
                    else:
                        spans.append(span)
                        if len(chunk_new) > 2:
                            chunks_new.append(chunk_new[:-2])
                        chunk_new = [str(span[0]), str(span[1])]
                        fragments.append(new_txt[span[0]:span[1]])
                else:
                    chunk_new = None
            if chunk_new is None:
                if not chunks_new:
                    break
            else:
                chunks_new.append(chunk_new)
        if spans:
            order_ = [i for _, i in sorted((x, i) for i, x in enumerate(spans))]
            spans = [spans[i] for i in order_]
            chunk_ = ' '.join(chunks_new[0])
            chunks_new_ = [chunks_new[i + 1] for i in order_]
            fragments_ = [fragments[i] for i in order_]
            end_pos = None
            chunks_new, fragments = [], []
            for span, chunk_new, fragment in zip(spans, chunks_new_, fragments_):
                if end_pos:
                    for c in new_txt[end_pos:span[0]]:
                        if c != ' ':
                            chunks_new.append(chunk_new)
                            fragments.append(fragment)
                            break
                    else:
                        chunks_new[-1][1] = chunk_new[1]
                        fragments[-1] += ' ' * (span[0] - end_pos) + fragment
                else:
                    chunks_new.append(chunk_new)
                    fragments.append(fragment)
                end_pos = span[1]
            chunks_new[0].insert(0, chunk_)
        if chunks_old and chunks_new:
            if chunks_new:
                chunks_new = ';'.join(' '.join(x) for x in chunks_new)
                if chunks_new in all_spans:
                    aid_map[aid] = all_spans[chunks_new]
                    continue
                all_spans[chunks_new] = aid
                chunks_new = [chunks_new]
            else:
                chunks_new = []
            new_ann.append(
                '\t'.join([aid] + chunks_new
                                + ([' '.join(fragments)] if fragments else
                                   ann[2:])))
            new_aids.add(aid)
    with io.open(save_new_ann_to, 'wt', encoding='utf=8', newline='\n') as f:
        if new_ann:
            f.write('\n'.join(new_ann) + '\n')

def renew_ann_dir(old_dir, new_dir, recursive=True, rewrite=False,
                  ignore_absent=False):
    """Runs `renew_ann()` method for all ann-files in the directory *old_dir*.
    The directory must also contain corresponding txt-files.

    The directory *new_dir* must contain new versions of the txt-files.
    Renewed ann-files will be also stored there.

    :param rewrite: if ``True``, don't throw an error if *new_dir* already
                    contain ann-files. In that case they will be rewritten.
                    Default is ``False``.
    :param ignore_absent: if ``True``, don't throw an error if some txt-file
                          in the *old_dir* directory doesn't have a
                          corresponding txt-file in the *new_dir*. Default is
                          ``False``.
    """
    for old_ann_fn in glob.glob(old_dir + '/**/*.ann', recursive=recursive):
        old_txt_fn = old_ann_fn[:-4] + '.txt'
        new_txt_fn = old_txt_fn.replace(old_dir, new_dir)
        new_ann_fn = new_txt_fn[:-4] + '.ann'
        assert os.path.isfile(old_txt_fn), \
            'ERROR: Can\'t find the file "{}"'.format(old_txt_fn)
        if not os.path.isfile(new_txt_fn):
            if ignore_absent:
                continue
            assert os.path.isfile(new_txt_fn), \
                'ERROR: Can\'t find the file "{}"'.format(new_txt_fn)
        assert rewrite or not os.path.isfile(new_ann_fn), \
            'ERROR: File "{}" is already exist'.format(new_txt_fn)
        renew_ann(old_txt_fn, old_ann_fn, new_txt_fn, new_ann_fn)
