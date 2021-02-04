# -*- coding: utf-8 -*-
# Toxine project: Text Preprocessing pipeline
#
# Copyright (C) 2019-present by Sergei Ternovykh
# License: BSD, see LICENSE for details
"""
Tag emojis, emails, dates, phones, urls, html/xml fragments etc.
Tag tokens with unallowed symbols.
Punctuation correction.
Tokenization.
"""
import datetime
from collections import OrderedDict
from functools import reduce
from html import unescape
from nltk import sent_tokenize as nltk_sent_tokenize, \
                 word_tokenize as nltk_word_tokenize
from pymorphy2 import MorphAnalyzer
from re import compile as re_compile, findall as re_findall, \
               match as re_match, search as re_search, split as re_split, \
               sub as re_sub
import sys
import uuid

from corpuscula import Conllu, CorpusDict
from corpuscula.utils import LOG_FILE, print_progress

word_is_known = MorphAnalyzer().word_is_known


class TextPreprocessor:

    def __init__(self, cdict_restore_from=None, cdict_corpus=None,
                 cdict_backup_to=None):
        """Init all internal constants.
        Run it before use any other function from the package.

        :param cdict_restore_from:
        :param cdict_corpus:
        :param cdict_backup_to:
        Params for CorpusDict's constructor.
        """
        self._cdict = CorpusDict(
            restore_from=cdict_restore_from, corpus=cdict_corpus,
            backup_to=cdict_backup_to
        )
        if self._cdict.isempty():
            self.wform_isknown = word_is_known
        else:
            self.wform_isknown = \
                lambda x: self._cdict.wform_isknown(x) or word_is_known(x)

        self._corpus = OrderedDict()

        self.TAG_MASKS = {}

        self.CHAR_DELIM = '|'
        re_char_delim = '\\' + self.CHAR_DELIM

        self.CHARS_PUNCT_ASIS = '+.,:;!?-'
        self.CHARS_PUNCT = '()/"\'«»“”„‟' + self.CHARS_PUNCT_ASIS
        self.CHARS_CURRENCY = '$¢£¤¥Ұ' \
                            + ''.join(chr(x) for x in range(0x20a0, 0x20d0))  # '₠₡₢₣₤₥₦₧₨₩₪₫€₭₮₯₰₱₲₳₴₵₶₷₸₹₺₻₼₽₾₿...'
        self.CHARS_ALLOWED = '_%&~№0-9A-Za-zЁА-Яёа-я`’²³°' \
                           + self.CHARS_CURRENCY + self.CHARS_PUNCT #+ 'єіїўқҳ'
        self.CHARS_CAPITAL = ''.join(chr(i) for i in range(2**16)
                                                if chr(i).istitle()
                                               and chr(i).isalpha())
        self.CHARS_REGULAR = ''.join(
            chr(i) for i in range(2**16) if chr(i) not in self.CHARS_CAPITAL
                                        and chr(i).isalpha()
        )
        self._CAPS = '[' + self.CHARS_CAPITAL + ']'
        self._NOCA = '[^' + self.CHARS_CAPITAL + ']'
        self._NOCASP = '[^' + self.CHARS_CAPITAL + '\s]'
        self._REGU = '[' + self.CHARS_REGULAR + ']'
        self._CARE = self._CAPS + self._REGU

        self.RE_LF = re_compile(r'([' + self.CHARS_PUNCT_ASIS + '])\n+')
        self.RE_LF2 = re_compile(r'([^' + self.CHARS_PUNCT_ASIS + '])\n+\s*('
                               + self._NOCA + r')')

        char_alpha  = r'A-Za-zЁА-Яёа-я'
        char_alnum  = r'0-9' + char_alpha
        char_alnum_ = char_alnum + '_'
        self.CHAR_NONALPHA  = '[^' + char_alpha   + ']'
        self.CHAR_ALPHA     = '['  + char_alpha   + ']'
        self.CHAR_NONALNUM  = '[^' + char_alnum   + ']'
        self.CHAR_ALNUM     = '['  + char_alnum   + ']'
        self.CHAR_NONALNUM_ = '[^' + char_alnum_  + ']'
        self.CHAR_ALNUM_    = '['  + char_alnum_  + ']'
        self.RE_EMOJI = re_compile(r'''(?xmu)
            (?:
                (''' + self.CHAR_ALNUM + ''')             # 1
                (    :-?[)\]}([{\\/|!]+)                  # 2
                (\.|\s|$)                                 # 3
            )|(?:
                (^|\s)                                    # 4
                ([:8Ж]-?[)\]}([{\\/|!]+)                  # 5
                (\.|\s|$)                                 # 6
            )|(?:
                (^|\s|''' + self.CHAR_ALNUM + ''')        # 7
                (;-?\)+ | [-=][)(]+ | -_- | ^-^)          # 8
                (\.|\s|$)                                 # 9
            )|(?:
                ([\u2660-\u27ff\U00010000-\U0010ffff])    # 10
                (?!\#\S*)  # skip hashtags
            )|(?:
                (^|[^)(:;=-])                             # 11
                (\)\)+ | \(\(+)                           # 12
            )|(?:
                (^[^(]*) (^|[^)(:;=-]) (\)+)              # 13-15
            )|(?:
                (\(+) ([^)(:;=-]|$) ([^)]*$)              # 16-18
            )|(?:
                <img\sclass='emoji\scode(\d\d\d\d)'[^>]+>
                \sЯндекс\sУсловия\sиспользования\s*$      # 19
            )
        ''')
        self.TAG_EMOJI = self.register_tag('EntityEmoji')
        self.TAG_EMO = 'EMO' + self.TAG_EMOJI
        self.RE_EMAIL = re_compile(r'''(?ximu)
            (?: mailto: )?
            (
                [a-z0-9!#$%&'*+/=?^_`{|}~-]+
                (?:
                    \.[a-z0-9!#$%&'*+/=?^_`{|}~-]+
                )*|"(?:
                     [\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]
                 | \\[\x01-\x09\x0b\x0c\x0e-\x7f]
                )*"
            )\s?@\s?(
                (?:
                    [a-z0-9]        # начинается с alphanum
                    (?:
                        [a-z0-9-]*  # в середине м.б. дефис
                        [a-z0-9]    # в конце только alphanum
                    )?
                    \.              # последний элемент - точка
                )+              # таких элементов не меньше 1
                [a-z0-9]        # последний элемент начинается с alpnanum
                (?:
                    [a-z0-9-]*  # в середине м.б. дефис
                    [a-z0-9]    # в конце только alphanum
                )?
                | \[(?:
                    (?: 25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]? )\.
                ){3}(?:
                    25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]? | [a-z0-9-]*[a-z0-9]:
                    (?:
                        [\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]
                    | \\[\x01-\x09\x0b\x0c\x0e-\x7f] )+
                )\]
            )
        (?!\S*''' + re_char_delim + ''')''')
        self.TAG_EMAIL = self.register_tag('EntityEmail', mask='адрес')
        self.RE_XML = re_compile(r'''(?ximu)
            (?:
                <
                    (?:               # вначале символ "<" (открыли тэг); за ним либо:
                        ([a-z:]+)     #     буквы и знак ":" (имя тэга)
                        (?:\s[^>]+)?  #     потом м.б. пробел и дальше всё кроме ">",
                    >                 #     а ">" завершает тэг
                    (?:
                        .*            #     потом любые символы,
                        </\1>         #     а завершается всё закрывающим тэгом "</имя тэга>";
                    )?                #     но этого м. и не быть
                )|                    # либо:
                </([a-z:]+)>          #     оборванный закрывающий тэг
            )                               # (типа, конец есть, а начало потерялось)
        (?!\S*''' + re_char_delim + ''')''')
        self.TAG_XML = self.register_tag('EntityXml')
        # scheme <sss>:[//]
        re_1 = r'''[^\s:]*[^a-z:+.-]'''  # garbage
        re_2 = r'''[a-z][0-9a-z+.-]*'''
        re_uri_scheme = r'''(?:
            ( (?:{})? )   ( (?: {} : )+ )   ( // )?
        )'''.format(re_1, re_2)
        # username[:password] <sss>[:<sss>]@
        re_1 = r'''[0-9a-z_.-]'''
        re_2 = r'''[0-9a-z_$&~*+=.,;!()-] | [%][0-9a-f][0-9a-f]'''
        re_uri_user = r'''(?:
                      ( (?:{})+ )
            (?:   :   ( (?:{})+ )   )?
                  @
        )'''.format(re_1, re_2)
        # host[:port] <sss[.sss][...]>[:<ddd>]
        re_1 = r'''[0-9a-zёа-я]   (?: [0-9a-zёа-я-]*[0-9a-zёа-я] )?'''
        re_uri_host = r'''(?:
            (   {} (?: \. {} )*   )
            (?:   :   ( \d+ )   )*
        )'''.format(re_1, re_1)
        # path </sss[/sss][...]>
        re_1 = r'''[0-9a-zёа-я_@$&~+=.,:!()-] | [%][0-9a-f][0-9a-f]'''
        re_uri_path = r'''(
            (?: / (?:{})* )+
        )'''.format(re_1)
        # params <;sss[=[sss]][;sss[=[sss]]][...]>
        re_1 = r'''[0-9a-zёа-я_@$&~*/+.,:!()-] | [%][0-9a-f][0-9a-f]'''
        re_uri_params = r'''(
            (?:   ;+ (?:{})+   (?: = (?:{})* )?   )+
        )'''.format(re_1, re_1)
        # query <?sss=sss&sss=sss&sss=sss>
        re_1 = r'''[0-9a-zёа-я_@$~*/+.,:;!()-] | [%][0-9a-f][0-9a-f]'''
        re_uri_query = r'''(
                 \? (?:{})+   (?: = (?:{})* )?
            (?:   & (?:{})+   (?: = (?:{})* )?   )*
        )'''.format(re_1, re_1, re_1, re_1)
        # fragment #<sss>
        re_1 = r'''[0-9a-zёа-я_@$&~*/+=.,:;!()-] | [%][0-9a-f][0-9a-f]'''
        re_uri_fragment = r'''(?:
            \# ({})*
        )'''.format(re_1)
        self.RE_URI = re_compile(r'''(?ximu)
            # https://www.ietf.org/rfc/rfc3986.txt
            #(?:([^:/?#]+):)? # scheme
            #(?://([^/?#]*))? # net_loc
            #([^?#]*)         # path
            #(?:\?([^#]*))?   # query
            #(?:#(.*))?       # fragment

            # https://www.w3.org/Addressing/rfc1808.txt
            (              # uri/1
                \b
                {0}?       # scheme/2
                {1}?       # username[:password]/3,4
                {2}?       # host[:port]/5,6
                {3}?       # path/7
                {4}?       # params/8
                {5}?       # query/9
                {6}?       # fragment/10
            )
        (?!\S*{7})'''.format(re_uri_scheme, re_uri_user, re_uri_host,
                             re_uri_path, re_uri_params, re_uri_query,
                             re_uri_fragment, re_char_delim))
        self.TAG_URI = self.register_tag('EntityUri', mask='адрес')
        self.RE_PHONE = re_compile(r'''(?ximu)
            (^|\D)                                     # 1 TODO: 20(040)420-12-46 --> 20(ENTITY_PHONE
            (\+?\d)?                                   # 2
            #(\+7|7|8)?                                 # 2
            \s?(?:\(|-)?\s? (\d{3,5}) \s?(?:\)|-)?\s?  # 3
            (\d{1,3})\s?\-?\s?                         # 4
            (\d\d)\s?\-?\s?                            # 5
            (\d\d)                                     # 6
            ([^-0-9''' + re_char_delim + ''']|$)       # 7
        (?!\S*''' + re_char_delim + ''')''')
        self.TAG_PHONE = self.register_tag('EntityPhone', mask='номер')
        self.RE_DATE = re_compile(
            r'(?mu)\b(\d\d?)\.(\d\d?)\.(\d\d(?:\d\d)?)(\b|г)'
            r'(?!\S*' + re_char_delim + ')'
        )
        self.TAG_DATE = self.register_tag('EntityDate', mask='сегодня')
        self.RE_HASHTAG = re_compile(
#            r'(?mu)(^|[\s(])(#' + self.CHAR_ALPHA + self.CHAR_ALNUM_
#            r'(?mu)(.)?(#' + self.CHAR_ALNUM_
            r'(?mu)(^|[\s(])?(#[' + char_alnum_
          + '\u2660-\u27ff\U00010000-\U0010ffff]'
          + r'{,138})(?!\S*' + re_char_delim + ')'
#          + r'{,138})\b(?!\S*' + re_char_delim + ')'
        )
        self.TAG_HASHTAG = self.register_tag('EntityHashtag')
        self.RE_NAMETAG = re_compile(
            r'(?mu)(^|[\s(])(@[A-Za-z0-9._]'# + self.CHAR_ALPHA + self.CHAR_ALNUM_
          + r'{,138})\b(?!\S*' + re_char_delim + ')'
        )
        self.TAG_NAMETAG = self.register_tag('EntityNametag', mask='ссылка')
        re_1 = r'\s*[A-ZЁА-Я][^"]+[.!?](?:\s*[A-ZЁА-Я][^"])*'
        self.RE_QUOTATION = re_compile(r'''(?xmu)
            (?:(")({0})("))|    # 1 - 3
            (?:(``)({0})(''))|  # 4 - 6
            (?:(«)({0})(»))|    # 7 - 9
            (?:(„)({0})(“))     # 10 - 12
        '''.format(re_1))
        self.TAG_QUOTATION_START = self.register_tag('QuotationStart', '``')
        self.TAG_QUOTATION_END = self.register_tag('QuotationEnd', "''")

        self.RE_TAG = re_compile(
            r'([^' + re_char_delim + r'\s]+)' + re_char_delim
          + r'([^' + re_char_delim + r'\s]+)')
        self.TAG_UNK = self.register_tag('EntityUnk')

        self.SHORTCUTS = []
        self.TAG_SHORTCUT = self.CHAR_DELIM + self.CHAR_DELIM + 'Shortcut'

    def add_shortcut(self, orig, subst):
        res = ''
        for subst_ in subst.split():
            idx = len(self.SHORTCUTS)
            res += '{}{}{}' \
                       .format('' if orig else ' ', idx, self.TAG_SHORTCUT)
            self.SHORTCUTS.append((subst_, orig))
            orig = ''
        return res

    def clear_corpus(self):
        self._corpus = OrderedDict()

    def new_doc(self, doc_id=None, metadata=None):
        """Create an empty document.

        :param doc_id: id of the document. If None then uuid will be used
        :type doc_id: str
        :param metadata: CoNLL-U metadata that will be returned in document
                         header
        :type metadata: OrderedDict
        :return: id of the document created
        :rtype: str
        """
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        self._corpus[doc_id] = \
            {'meta': OrderedDict(metadata if metadata else [])}
        return doc_id

    def remove_doc(self, doc_id):
        """Remove the document with a given *doc_id*"""
        self._corpus.pop(doc_id, None)

    def new_par(self, text, doc_id=None):
        """Add a *text* as a paragraph to the document.

        :param doc_id: id of the document. If None then new document will be
                       created
        :type doc_id: str
        :return: number of a paragraph created
        :rtype: int
        """
        return self.new_pars([text], doc_id)[0]

    def new_pars(self, pars, eop=r'\n', doc_id=None):
        """Add a list of text blocks as paragraphs to the document. Empty
        blocks will be skipped.

        :param pars: paragraphs to add. If pars is of str type, it will be
                     splitted first with ``text_to_pars()``
        :type pars: list(str)|str
        :param eop: param for ``text_to_pars()``. Ignored if *pars* not of str
                    type
        :param doc_id: id of the document. If None then new document will be
                       created
        :type doc_id: str
        :return: lower and higher numbers of paragraphs created
        :rtype: tuple(int, int)
        """
        if doc_id is None:
            doc_id = self.new_doc()
        assert doc_id in self._corpus, \
            'ERROR: document "{}" has not exist'.format(doc_id)
        doc = self._corpus[doc_id]
        pars_ = doc.setdefault('pars', [])
        par_no1 = len(pars_)
        par_no2 = par_no1 - 1
        for i, text in enumerate(
            self.text_to_pars(pars, eop=eop) if isinstance(pars, str) else
            pars,
            start=par_no1
        ):
            assert isinstance(text, str), \
                "ERROR: text must be of 'str' type (line {})" \
                    .format(i)
            if text:
                pars_.append({'text': self.RE_LF2.sub(
                    r'\g<1> \g<2>', self.RE_LF.sub(r'\g<1> ', text)
                ).replace('\n', '. ').replace('\r', '')})
                par_no2 += 1
        return (par_no1, par_no2) if par_no2 >= par_no1 else (None, None)

    def load_pars(self, path, encoding='utf-8-sig', eop=r'\n', doc_id=None):
        """Load a text, split it into paragraphs, and put to the document.

        :param path: a name of a file in txt format
        :param eop: param for ``text_to_pars()``
        :param doc_id: id of the document. If None then new document will be
                       created
        :type doc_id: str
        :return: lower and higher numbers of paragraphs created
        :rtype: tuple(int, int)
        """
        res = (None, None)
        print('Load corpus...', end=' ', file=LOG_FILE)
        LOG_FILE.flush()
        with open(path, mode='rt', encoding=encoding) as f:
            res = self.new_pars(list(self.text_to_pars(f.read(), eop=eop)),
                                doc_id)
        print('done.', file=LOG_FILE)
        return res

    @staticmethod
    def text_to_pars(text, eop=r'\n'):
        """Just split a *text* into paragraphs by a given rule. Empty
        paragraphs will be skipped.

        :param text: text to split
        :type text: str
        :param eop: regex or function for splitting a *text*. If None then
                    all the *text* will be placed into one paragraph. Default
                    is LF symbol
        :type eop: str|callable
        :rtype: iter(list(str))
        """
        return filter(bool, map(lambda x: x.strip(),#.replace('\u00A0', ' '),
                                eop(text) if callable(eop) else
                                re_split(eop, text))) if eop else \
               [text]

    def _unescape_html(self, text):
        """Convert html entities (&gt;, &#62;, &x3e;) to the corresponding
        characters"""
        #text = re_sub(r'(&[a-z]+;)', r' \g<1> ', text)
        return unescape(text)

    def _preprocess_emoji_default(self, text):
        """Depending on CHAR_DELIM symbol, replace emojis of type ":-\" to
        ":-/" (for '\\') or ":-|" to ":-!" (for '|')"""
        return re_sub(r'(^|\s|' + self.CHAR_ALNUM
                    + r')(:-?\\+)(\s|$)', r'\g<1>:-/\g<3>', text) \
                   if self.CHAR_DELIM == '\\' else \
               re_sub(r'(^|\s|' + self.CHAR_ALNUM \
                    + r')(:-?\|)(\s|$)', r'\g<1>:-!\g<3>', text)  \
                   if self.CHAR_DELIM == '|' else \
               text

    def _remove_delims(self, text, sub=' '):
        """Remove a characters further using for a tagging from a *text*.
        If *delim* is None, using a value set during ``__init__()``.

        :param text: text to process
        :type text: str
        :param sub: substitute for a removing characters
        :type sub: str
        """
        return self._preprocess_emoji_default(text) \
                   .replace(self.CHAR_DELIM, sub)

    def _tag_emoji(self, text):
        """NOTE: Some emojis may become corrupted after ``remove_delims()``.
        You need to change them prior. For default *delim* symbol just run
        ``preprocess_emoji_default()`` before ``remove_delims()``
        TODO: Need to add more complete emojis support"""
        text = self.RE_EMOJI.sub(
            lambda x:
                (x.group(1) + ' ' + x.group(2) + self.TAG_EMOJI + ' '
                                                                  + x.group(3)
                     if x.group(2) else '')
              + (x.group(4) + x.group(5) + self.TAG_EMOJI + ' ' + x.group(6)
                     if x.group(5) else '')
              + (x.group(7) + ' ' + x.group(8) + self.TAG_EMOJI + ' '
                                                                  + x.group(9)
                     if x.group(8) else '')
              + (' ' + x.group(10) + self.TAG_EMOJI + ' '
                     if x.group(10) else '')
              + (x.group(11) + ' ' + x.group(12) + self.TAG_EMOJI + ' '
                     if x.group(12) else '')
              + (x.group(13) + x.group(14) + ' ' + x.group(15)
                                                        + self.TAG_EMOJI + ' '
                     if x.group(15) else '')
              + (' ' + x.group(16) + self.TAG_EMOJI + ' ' + x.group(17)
                                                                 + x.group(18)
                     if x.group(16) else '')
              + (' yandex_' + x.group(19) + self.TAG_EMOJI
                     if x.group(19) else ''),
            text
        )
        return text

    def _tag_email(self, text):
        text = self.RE_EMAIL.sub(r' \g<1>@\g<2>' + self.TAG_EMAIL + ' ', text)
        return text

    def _tag_xml(self, text):
        text = self.RE_XML.sub(r' \g<1>\g<2>' + self.TAG_XML + ' ', text)
        return text

    def _tag_uri(self, text):
        def process(match):
            uri, garbage, scheme, scheme_tail, user_login, user_passwd, \
                host, port, path, params, query, fragment = match.groups()
            scnt = scheme.count(':') if scheme else -1
            hcnt =   host.count('.') if   host else -1
            isuri = (
                scheme and (path or query)
            ) or (
                # есть схема, а в хосте хотя бы одна точка, и при этом
                # в домене хоста либо только латинские буквы, либо конкретные
                # доменные зоны, либо хост - это ровно 4 числа (ip-адрес)
                ((scheme and hcnt >= 0) or hcnt >= 2) and re_search(r'''(?xiu)
                    ^
                    (?:
                        (?:
                            (?: [ёа-я]+ [.-]? )?                         # head
                            # only ascii
                            (?: [0-9a-z][0-9a-z-]*\. )*
                            (?: [a-z][a-z-]+ )           # java errors included
                                        # '{1,10}' instead of '+' for http uris
                        )|(?:
                            # known cyrillic zones
                            (?:
                                (?:
                                     [0-9a-z][0-9a-z-]*
                                |
                                    [0-9ёа-я][0-9ёа-я-]*
                                )
                                \.
                            )+
                            (?: бг | бел | рф | срб | укр )  # don't add 'ru'!
                        )
                    )
                    (?: [.-] [ёа-я]+ )?                                  # tail
                    $
                ''', host)
            ) or (
                # <scheme>://<ip-addr>
                scheme and scheme_tail and hcnt == 3
            and not re_search('[^0-9.]', host)
            and reduce(lambda y, x: x >= 0 and x <= 255 and y,
                       map(int, re_findall(r'\b(\d{1,3})\b', host)), True)
            ) or (
                # поддерживаем urn'ы
                scnt >= 2 and host
            )
            # workaround for english names:
            toks = match.group(0).split('.')
            if re_match('(?:[A-Z]\.){1,4}[A-Z][A-Za-z]+', match.group(0)):
                res = match.group(0).replace('.', '. ')
            elif isuri:
                head = tail = None
                if host and not (scheme and user_login and user_passwd):
                    head = re_search('^([ёа-я]+[.-]?)[0-9a-z]', host)
                    if head:
                        head = head.group(1)
                        uri = uri[len(head):]
                if path or params or query or fragment:
                    tail = re_search('(?i)([.,:;!()-]+[ёа-я]*)$', uri)
                elif host:
                    tail = re_search(
                        '(?i)(?=(?!\.(?:бг|бел|рф|срб|укр)$))([.-][ёа-я]+)$',
                        uri
                    )
                if tail:
                    tail = tail.group(1)
                    #uri = uri.rsplit(tail, 1)[0]
                    uri = uri[:-len(tail)]
                if garbage:
                    uri = uri[len(garbage):]
                res = (garbage if garbage else '') \
                    + (head if head else '') \
                    + ' ' + uri + self.TAG_URI + ' ' \
                    + (tail if tail else '')
            else:
                res = match.group(0)
            return res
        text = self.RE_URI.sub(process, text)
        return text

    def _tag_phone(self, text):
        def process(match):
            pre, p1, p2, p3, p4, p5, post = match.groups()
            if p1 not in ('', '+7', '7', '8'):
                res = match.group(0)
            else:
                phone = p2 + p3 + p4 + p5
                if len(phone) == 11 and phone[0] in ('7', '8'):
                    phone = phone[1:]
                res = '{} +7{}{} '.format(pre, phone, self.TAG_PHONE) \
                    if len(phone) == 10 else match.group(0)
            return res
        text = self.RE_PHONE.sub(process, text)
        return text

    def _tag_date(self, text):
        def process(match):
            res = match.group(0)
            d, m, y = int(match.group(1)), int(match.group(2)), match.group(3)
            if len(y) == 2: y = '20' + y
            y = int(y)
            end = match.group(4)
            try:
                if y > 1900 and y < 2030:
                    res = ' ' + str(datetime.date(y, m, d)) + self.TAG_DATE + \
                          ' ' + (end if end else '')
            except ValueError:
                pass
            return res
        text = self.RE_DATE.sub(process, text)
        return text

    def _tag_hashtag(self, text):
        text = self.RE_HASHTAG.sub(
            r'\g<1> \g<2>' + self.TAG_HASHTAG + ' ', text
        )
        return text

    def _tag_nametag(self, text):
        text = self.RE_NAMETAG.sub(
            r'\g<1> \g<2>' + self.TAG_NAMETAG + ' ', text
        )
        return text

    def _tag_quotation(self, text):
        def process(match):
            res = match.group(0)
            for i in range(1, 12, 3):
                q1 = match.group(i)
                if q1:
                    q2, q3 = match.group(i + 1), match.group(i + 2)
                    res = q1 + self.TAG_QUOTATION_START + ' ' \
                        + q2 + ' ' \
                        + q3 + self.TAG_QUOTATION_END + ' '
                    break
            return res
        text = self.RE_QUOTATION.sub(process, text)
        return text

    def norm_punct(self, text, islf_eos=True, istab_eos=True,
                   ignore_case=False):
        """Some heuristics to normalize Russian punctuation. Use it for chat
        or forum messages where illiterate people are prevail. If your content
        is already correct, you don't need this method.

        :param islf_eos: LF symbol marks end of sentence; replace to "."
        :param istab_eos: TAB symbol marks end of sentence; replace to "."
        :param ignore_case: do not consider character case during processing
        """
        flags = re.I if ignore_case else 0
        if islf_eos:
            text = text.replace('\n', ' . ')
        if istab_eos:
            text = text.replace('\t', ' . ')

        wform_isknown = self.wform_isknown

        # ; -> .
        text = text.replace(';', ' . ')
        # пробелы между знаками препинания
        _chars_punct = '([' + self.CHARS_PUNCT + '])'
        _chars_punct += '\s+' + _chars_punct
        text = re_sub(_chars_punct, r'\g<1>\g<2>', text)
        text = re_sub(_chars_punct, r'\g<1>\g<2>', text)  # sic!
        # лишние запятые
        text = re_sub(r',*([.!?]),*', r'\g<1>', text)
        # необычные сочетания всяких символов - конец предложения
        text = re_sub(r'---+|,,,+|~+|\'\'\'+|"""+|№№№+', r' . ', text)
        # два символа - в один
        text = text.replace(r'--', r' - ')
        text = text.replace(r"''", r' " ')
        text = text.replace(r'""', r' " ')
        text = re_sub(r',,?', r' , ', text)
        text = re_sub(r'№№?', r' № ', text)
        # апостроф в начале или в конце строки - кавычки
        text = re_sub(r"^'|'$", '"', text)
        # если несколько символов ., ?, !, подряд, то если среди них есть
        # ?, то меняем всё на него, если есть !, то на него, иначе ставим
        # три точки
        text = re_sub(r'[.?!]{2,}',
                      lambda x: ' ' + re_sub(r'.*\..*', '...',
                                             re_sub(r'.*\!.*', '!',
                                                    re_sub(r'.*\?.*', '?',
                                                           x.group(0)))) + ' ',
                      text)

        # === PERIODS ===
        # ---------------

        # --- names ---
        # инициал: одна заглая буква; м.б. 1 или 2 инициала
        # фамилия: с заглавной буквы; не меньше двух символов;
        #          если в середине дефис, то обе части фамилии
        #          с заглавной буквы и каждая не меньше двух символов
        for re_lname, re_init in [
            (  r'[A-Z](?:[a-z]+-[A-Z])?[a-z]+'  ,  r'[A-Z]\.'),
            (r'[ЁА-Я](?:[ёа-я]+-[ЁА-Я])?[ёа-я]+', r'[ЁА-Я]\.')
        ]:
            # инициалы в начале:
            text = re_sub(r'\b({0})({0})? ?({1})\b'
                              .format(re_init, re_lname),
                          r' \g<1> \g<2> \g<3> ', text, flags=flags)
            # инициалы в конце:
            text = re_sub(r'\b({1}) ({0})({0})?\b'
                              .format(re_init, re_lname),
                          r' \g<1> \g<2> \g<3> ', text, flags=flags)

        # --- end of sentence w/o space after period ---
        def process(match):
            a, b = match.groups()
            return a + '. ' + b if b.lower() not in [
                'com', 'org', 'edu', 'net', 'info',
                'de', 'cn', 'uk', 'ru', 'su', 'us', 'jp',
                'бг', 'бел', 'рф', 'срб', 'укр'
            ] and (wform_isknown(a) or wform_isknown(b)) else match.group(0)
        text = re_sub(r'(\w+)\.(\w+)', process, text)
        text = re_sub(r'(\w+)\.(\w+)', process, text)  # sic!

        # period just before a word
        text = re_sub(r'(^|\W)\.(\w)', r'\g<1>. \g<2>', text)

        # period before of quotation:
        text = re_sub(r'(\w+)\.\s*(["`«„]\s*\b)', r'\g<1> . \g<2>', text)

        # known bugs of russian nltk punkt:
        text = re_sub(r'\b(я|театр|нас|прав)\.', r'\g<1> .', text)

        # --- known shortcuts ---
        '''
        re_0 = r'\b'
        re_1 = r'\b\.?\s*([ЁА-Я])?' # конец слова; дальше м.б. точка и/или
                                    # заглавная буква через пробелы или без
                                    # них
        re_2 = r'\s*\.?\s*'
        re_3 = r'\b\s*\.?\s*'       # конец слова, после которого возможны
                                    # пробелы и/или точка
        re_4 = r'\s*'
        re_5 = r'\s+'
        #TODO: capitalization
        for a, b in [(r'{0}[иИ]{4}т{2}д{1}', r'и так далее'),
                     (r'{0}[иИ]{4}т{2}п{1}', r'и тому подобное'),
                     (r'{0}[мМ]{3}б{1}',     r'может быть'),
                     (r'{0}[тТ]{3}е{1}',     r'то есть'),
                     (r'{0}[тТ]{2}к{1}',     r'так как')]:
            text = re_sub(a.format(re_0, re_1, re_2, re_3, re_4, re_5),
                          # если после сокращения идёт слово
                          # с заглавной буквы, то ставим перед ним точку
                          lambda x: ' {} {}'
                                        .format(b, ('. ' + x.group(1))
                                                       if x.group(1) else ''),
                          text)
        for a, b in [(r'{0}г-ж([аеиу]|ой){0}', r'госпож\g<1>'),
                     (r'{0}г-н([аеу]|ом)?{0}', r'господин\g<1>')]:
            text = re_sub(a.format(re_0), ' {} '.format(b), text)
        '''
        re_0 = r'\b'
        re_1 = r'\s*([ЁА-Я])?'  # заглавная буква через пробелы или без них
        re_2 = r'\b\s*\.?'      # конец слова, после которого возможны пробелы
                                # и/или точка
        re_3 = re_2 + r'\s*'    # то же, что и re_2, но в конце ещё может быть
                                # пробел
        re_4 = r'\s*'
        re_5 = r'\s+'
        #TODO: capitalization
        for a, b in [(r'({0}[иИ]{4}т{2}д{2}){1}',  r'и так далее'),
                     (r'({0}[иИ]{4}т{2}п{2}){1}',  r'и тому подобное'),
                     (r'({0}[мМ]{3}б{2}){1}',      r'может быть'),
                     (r'({0}[тТ]{3}е{2}){1}',      r'то есть'),
                     (r'({0}[тТ]{3}к{2}){1}',      r'так как')]:
            text = re_sub(a.format(re_0, re_1, re_2, re_3, re_4, re_5),
                          # если после сокращения идёт слово
                          # с заглавной буквы, то ставим перед ним точку
                          lambda x: ' {} {}'
                                        .format(self.add_shortcut(x.group(1),
                                                                  b),
                                                ('. ' + x.group(2))
                                                    if x.group(2) else ''),
                          text)
        for a, b in [(r'({0}г-ж([аеиу]|ой){0})', r'госпож'),
                     (r'({0}г-н([аеу]|ом)?{0})', r'господин')]:
            text = re_sub(a.format(re_0),
                          lambda x: ' {} '.format(
                              self.add_shortcut(x.group(1),
                                                b + (x.group(2)
                                                         if x.group(2) else
                                                     ''))
                          ),
                          text)

        # === HYPHENS ===
        # ---------------

        # --- searching dashes between hyphens ---
        def process(match):
            # если один из токенов - наш тэг, то ничего не меняем
            if self.CHAR_DELIM in [match.group(1), match.group(3)]:
                return match.group(0)

            token = match.group(2)
            # сохраняем разделители
            hyphens = re_findall('\W+', token)

            res = ''
            words = token.replace(' ', '').split('-')
            test_word = '{}-{}'.format(words[0], words[1])
            if len(words) == 2 and (
                wform_isknown(test_word) or (
                    words[0].isdecimal() and words[1].isalpha()
                )
            ):
                return '{}-{}'.format(words[0], words[1])
            # поиск:                   -i-
            #                 [xxx....] 0
            #                 [.xxx...] 1
            #        [xx.....][..xxx..] 2
            #        [_xx....][...xxx.] 3
            #        [__xx...][....xxx] 4
            #        [___xx..]          5
            #        [____xx.]          6
            #        [_____xx]          7
            # проверяем на реальность тройные и двойные сочетания слов с дефисами
            # и без них
            len_words = len(words)
            last_3 = len_words - 3
            i = 0
            maybehyphen = -1 # -1: absolutely never (i == 0)
                             #  0: never (word with hyphen have just been added)
                             #  1: maybe (known word have just been added)
                             #  2: highly likely (unknown word have just been added)
            def add_word(i):
                nonlocal res, words, maybehyphen
                word = words[i]
                word_lower = word.lower()
                # если мы в самом начале или если у нас частица
                if maybehyphen == -1:
                    res += ' ' + word
                    maybehyphen = 2 - wform_isknown(word)
                # частые ошибки
                elif word_lower in ['бы', 'же', 'ли']:
                    res += ' ' + word
                    maybehyphen = 0
                # частые ошибки
                elif word_lower == 'равно' and \
                     words[i-1].lower().replace('ё', 'е') == 'все':
                    res += ' ' + word
                    maybehyphen = 0
                # если предыдущее слово - с дефисом, то ставим тире
                elif maybehyphen == 0:
                    res += ' - ' + word
                    maybehyphen = 2 - wform_isknown(word)
                else: # maybehyphen in [1, 2]
                    isknown = wform_isknown(word)
                    ## если и предыдущее, и текущее слово известны
                    if maybehyphen == 1 and isknown:
                        ## если автор не добавлял пробелов, то и мы не будем
                        #if hyphens[i-1] == '-': # safe... I think %)
                        #    res += '-' + word
                        #    #maybehyphen = 1
                        #else:
                        #    res += ' - ' + word
                        #    maybehyphen = 2
                        res += ' - ' + word
                        maybehyphen = 1
                    ## если хотя бы одно слово неизвестно, то дефис
                    else:
                        res += '-' + word

            while True:
                has1more = i > 0
                if i >= 2:
                    for word in [words[i - 2] + '-' + words[i - 1],
                                 words[i - 2] + ''  + words[i - 1]]:
                        if wform_isknown(word):
                            res += ' ' + word
                            has1more = False
                            maybehyphen = 0
                            break
                    else:
                        add_word(i - 2)
                if i >= len_words:
                    if has1more:
                        add_word(i - 1)
                    break
                if i <= last_3:
                    for word in [
                        words[i] + '-' + words[i + 1] + '-' + words[i + 2],
                        words[i] + ''  + words[i + 1] + '-' + words[i + 2],
                        words[i] + '-' + words[i + 1] +  '' + words[i + 2],
                        words[i] +  '' + words[i + 1] +  '' + words[i + 2]
                    ]:
                        if wform_isknown(word):
                            if has1more:
                                add_word(i - 1)
                            res += ' ' + word
                            words = words[i + 3:]
                            len_words = len(words)
                            last_3 = len_words - 3
                            i = 0
                            maybehyphen = 0
                            break
                    else:
                        i += 1
                else:
                    i += 1

            #print('{:40}{}'.format('(' + token + ')', '(' + res + ' )'))
            return res + ' '

        # находим все слова c дефисами; с одной стороны от дефиса м.б. пробел
        text = re_sub(r'(\{})?(\w+(?:(?:-| -|- )\w+)(\{})?)+'
                           .format(self.CHAR_DELIM, self.CHAR_DELIM),
                      process, text)

        # дефис в начале русского слова = тире
        text = re_sub(r'(^|[^0-9ЁА-Яёа-я])-([ЁА-Яёа-я])', '\g<1>- \g<2>',
                      text)
        # дефис после знака препинания = тире
        text = re_sub(r'([.!?])-(\s|$)', '\g<1> -\g<2>', text)

        return text

    def sent_tokenize(self, text, kill_empty=True):
        """Return sentence-tokenized copy of a *text*

        :rtype: list
        """
        text = text.replace('«', '``').replace('“', '``').replace('„', "``") \
                   .replace('»', "''").replace('”', "''").replace('‟', "''")

        sents_ = nltk_sent_tokenize(text, language='russian')

        re_ellipsis = re_compile(r'(\.\.\.)\s+([0-9A-ZЁА-Я])')
        def parse_el(sent):
            sents = []
            ellipsis = self.CHAR_DELIM + 'ellipsis' + self.CHAR_DELIM
            len_ellipsis = len(ellipsis)
            sent = re_ellipsis.sub(r'\g<1>{}\g<2>'.format(ellipsis), sent)
            i = 0
            while True:
                i = sent.find(ellipsis)
                if i == -1:
                     break
                sents.append(sent[:i])
                sent = sent[i + len_ellipsis:]
            if sent:
                sents.append(sent)
            return sents

        def notempty(text):
            return re_search(r'[0-9A-ZЁА-Я]', text)

        sents, is_join_candidate = [], False
        re_quot = re_compile(r'\d+' + '\\' + self.TAG_QUOTATION_END)
        for sent in sents_:
            match = re_quot.match(sent)
            if sents and match:
                quot = match.group(0)
                sents[-1] += ' ' + quot
                sent = sent[len(quot):]
                if not notempty(sent):
                    if sent:
                        if sent[0] in '!?.':
                            sents[-1] += sent
                        else:
                            sents.append(s)
                        ending = sent[-1]
                        if ending in '!?.':
                            is_join_candidate = True
                    continue
            for s_ in parse_el(sent):
                for s in parse_el(s_):
                    if is_join_candidate and s[0] in '!?.':
                        sents[-1] += s
                    else:
                        sents.append(s)
                    ending = s[-1]
                    if ending in '!?.':
                        is_join_candidate = True

        if kill_empty:
            sents = list(filter(notempty, sents))

        return sents

    @staticmethod
    def word_tokenize(text):
        """Return a word-tokenized copy of *text*

        :rtype: list
        """
        # NB: "" -> ``''
        tokens_ = nltk_word_tokenize(text, language='russian',
                                     preserve_line=True)
        tokens, is_join_candidate = [], False
        for token in tokens_:
            if is_join_candidate and token[0] in '!?.':
                tokens[-1] += token
            else:
                tokens.append(token)
            ending = token[-1]
            if ending in '!?.':
                is_join_candidate = True
        try:
            idx = tokens.index("'")
        except ValueError:
            try:
                idx = tokens.index('’')
            except ValueError:
                try:
                    idx = tokens.index('`')
                except ValueError:
                    idx = -1
        if idx > 0 and idx + 1 < len(tokens) \
                   and tokens[idx - 1].isalpha() \
                   and tokens[idx + 1].isalpha() \
                   and tokens[idx + 1].istitle():
            tokens = tokens[:idx - 1] \
                   + [tokens[idx - 1] + tokens[idx] + tokens[idx + 1]] \
                   + tokens[idx + 2:]
        return tokens

    @staticmethod
    def tokenize(text, kill_empty=True):
        """Return tokenized copy of *text*

        :rtype: list (sentences) of lists (words)
        """
        sents = sent_tokenize(text, kill_empty)
        res = []
        for sent in sents:
            if not kill_empty or re_search('(?i)[0-9a-zёа-я]', sent):
                words = word_tokenize(sent)
                res.append(words)
        return res

    def register_tag(self, tag, mask=None):
        """Add *tag* to the table of substitutions and return its internal
        form for using in external taggers"""
        tag_ = self.CHAR_DELIM + tag
        if tag_ in self.TAG_MASKS:
            print('WARNING: the tag '
                  '"{}" is already in use and will be replaced'
                      .format(tag),
                  file=LOG_FILE)
        self.TAG_MASKS[tag_] = mask
        return tag_

    def process_text(self, text, chars_allowed=None, unescape_html=True,
                     pre_tag=None, tag_emoji=True, tag_xml=True,
                     tag_email=True, tag_uri=True, tag_phone=True,
                     tag_date=True, tag_hashtag=True, tag_nametag=True,
                     post_tag=None, split_unk=False, tag_unk=True,
                     norm_punct=False, islf_eos=True, istab_eos=True,
                     ignore_case=False, silent=False, sent_no=0, tags={}):
        """Make preprocessing (including tokenization) for the given *text*

        :param chars_allowed: allowed charset (all allowed symbols for use in
                              "[]" regex)
        :type chars_allowed: str

        :param unescape_html: do we need to make back transformation from
                              escaped html

        :param pre_tag: external tagger (or just preprocessor) that will be
                        run before all internal taggers:

                        text = pre_tag(text, delim)

                        where delim is a character to separate tag signature
        :type pre_tag: callable

        :param tag_date:
        :param tag_email:
        :param tag_emoji:
        :param tag_hashtag:
        :param tag_nametag:
        :param tag_phone:
        :param tag_uri:
        :param tag_xml:
        Preprocessors we want to run. They will be started exactly in that
        order. May be callable with the same signature as for *pre_tag*.

        :param post_tag: external tagger (or just preprocessor) that will be
                         run after all internal taggers. The signature is the
                         same as for *pre_tag*: text = post_tag(text, delim).
        :type post_tag: callable
        :param split_unk: split tokens with disallowed chars, if these chars
                          placed only at the begin or/and at the end of the
                          token
        :param tag_unk: add special tag to the tokens with disallowed chars

        :param norm_punct: normalize punctuations. Use it if you process
                           text chats or forum messages
        Params for ``norm_punct()``:
        :param islf_eos: LF symbol marks end of sentence; replace to "."
        :param istab_eos: TAB symbol marks end of sentence; replace to "."
        :param ignore_case: do not consider character case during processing

        :param silent: suppress log
        :param sent_no: init value for the progress indicator (has effect if
                        silent is False)
        :param tags: storage for found tags
        :type tags: dict(tag, value)
        """
        assert pre_tag is None or callable(pre_tag), \
            'ERROR: ext_pre must be either callable or None'
        assert post_tag is None or callable(post_tag), \
            'ERROR: ext_post must be either callable or None'

        chars_allowed = r'\s' + (chars_allowed if chars_allowed else
                                 self.CHARS_ALLOWED)
        SUBS = [
            #кавычки
            #('\u00AB\u00BB\u2039\u203A\u201E\u201A\u201C\u201F\u2018\u201B'
            # "\u201D\u2019'", '"'),
            # тире
            ('\u2012\u2013\u2014\u2015\u203E\u0305\u00AF', ' - '),
            # дефис
            ('\u2010\u2011\u2212', '-'),
            # софт дефис - удалить
            ('\u00AD', ''),
            # пробел
            ('\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009'
             '\u200A\u202F\u205F\u2060\u3000', ' '),
            # пробел нулевой длины
            ('\u200B\uFEFF', ''),
            # остальное - десятичный разделитель, булит, диакритические точки,
            # интерпункт
            ('\u02CC\u0307\u0323\u2022\u2023\u2043\u204C\u204D\u2219\u25E6'
             '\u00B7\u00D7\u22C5\u2219\u2062', '.'),
            # астериск --> звездочка
            ('\u2217', '*'),
            # многоточие --> три точки
            ('…', '...'),
            # тильда
            ('\u2241\u224B\u2E2F\u0483', '~'),
            # скобки
            ('[{', '('),
            (']}', ')'),
            # лишние символы
            #('*_', ' ')
        ]

        RE_NOSPACE = re_compile(r'\S+')

        def process_re_tag(match):
            token, tag = match.groups()
            taglist = tags.setdefault(tag, [])
            tag = str(len(taglist)) + self.CHAR_DELIM + tag 
            taglist.append(token)
            return tag

        def process_re_nospace(match):

            token = match.group(0)
            if self.CHAR_DELIM not in token:
                for search, replace in SUBS:
                    for c in search:
                       if c in token:
                           token = token.replace(c, replace)
                # извращения
                if '<<' in token:
                    token = re_sub(r'<<<+', r' . ', token)
                    token = token.replace('<<', ' " ')
                if '>>' in token:
                    token = re_sub(r'>>>+', r' . ', token)
                    token = token.replace('>>', ' " ')

                _TAG_UNK = self.TAG_UNK.replace(self.CHAR_DELIM, '')

                isunk = re_search(r'[^ ' + chars_allowed + ']', token)
                if isunk:
                    # если вначале и/или в конце знаки пунктуации, то сохраняем их
                    p1 = p2 = ''
                    borders = re_findall(r'^([' + self.CHARS_PUNCT + ']*)'
                                         r'([^' + self.CHARS_PUNCT + ']+)'
                                         r'([' + self.CHARS_PUNCT + ']*)$',
                                         token)
                    if borders:
                        p1, token, p2 = borders[0]
                        borders = None

                    t1 = t2 = None
                    if split_unk:
                        # если недопустимые символы только вначале и/или в конце,
                        # то отделяем их от допустимых
                        borders = re_findall(r'^([^' + chars_allowed + ']*)'
                                             r'([' + chars_allowed + ']+)'
                                             r'([^' + chars_allowed + ']*)$',
                                             token)
                        if borders:
                            t1, token, t2 = borders[0]

                    if tag_unk:
                        if tags is None:
                            if borders:
                                if t1:
                                    t1 += self.TAG_UNK
                                if t2:
                                    t2 += self.TAG_UNK
                            else:
                                token += self.TAG_UNK
                        else:
                            taglist = tags.setdefault(_TAG_UNK, [])
                            token_ = str(len(taglist)) + self.TAG_UNK
                            if borders:
                                if t1:
                                    taglist.append(t1)
                                    t1 = token_
                                    if t2:
                                        token_ = str(len(taglist)) + self.TAG_UNK
                                if t2:
                                    taglist.append(t2)
                                    t2 = token_
                            else:
                                taglist.append(token)
                                token = token_
                    if t1:
                        token = t1 + '\u00AD' + token
                    if t2:
                        token = token + '\u00AD' + t2
                    token = p1 + ' ' + token + ' ' + p2
            return token

        if unescape_html:
            text = unescape_html(text) \
                       if callable(unescape_html) else \
                   self._unescape_html(text)

        text = self._remove_delims(text)

        def run_tagger(tagger, default_tagger):
            return tagger(text, self.CHAR_DELIM) if callable(tagger) else \
                   default_tagger(text) if tagger else \
                   text

        tag_quotation = True
        for tagger, default_tagger in zip(
            [pre_tag, tag_emoji, tag_xml, tag_email,
             tag_uri, tag_phone, tag_date, tag_hashtag,
             tag_nametag, tag_quotation, post_tag],
            [lambda x: x, self._tag_emoji, self._tag_xml, self._tag_email,
             self._tag_uri, self._tag_phone, self._tag_date, self._tag_hashtag,
             self._tag_nametag, self._tag_quotation, lambda x: x]
         ):
            text = run_tagger(tagger, default_tagger)

        text = self.RE_TAG.sub(process_re_tag, text)
        text = RE_NOSPACE.sub(process_re_nospace, text)
        if norm_punct:
            text = self.norm_punct(text, islf_eos=islf_eos,
                                         istab_eos=istab_eos,
                                         ignore_case=ignore_case)

        sents = self.sent_tokenize(text, kill_empty=True)
        sents_ = []
        #del par['text']
        for sent in sents:
            if not silent and not sent_no % 100:
                print_progress(sent_no, end_value=None, step=1000,
                               file=LOG_FILE)
            sent_no += 1
            #if re_search('(?i)[0-9a-zёа-я]', sent):
            wforms = self.word_tokenize(sent)
            tokens = Conllu.from_sentence(wforms)
            text = ''
            space_before = False
            for i, token in enumerate(tokens):
                wform = token['FORM']
                delim_pos = wform.find(self.CHAR_DELIM)
                misc = token['MISC']
                if delim_pos >= 0:
                    idx = int(wform[:delim_pos])
                    tag = wform[delim_pos:]
                    if tag == self.TAG_SHORTCUT:
                        subst, orig = self.SHORTCUTS[idx]
                        token['FORM'] = subst
                        misc[self.TAG_SHORTCUT[2:]] = orig
                    else:
                        mask = self.TAG_MASKS[tag]
                        tag = tag[1:]
                        orig = tags[tag][idx]
                        #token = tokens[i]
                        token['FORM'] = mask
                        misc[tag] = orig
                        if space_before:
                            text += ' '
                        text += orig
                elif wform in ['``', '(', '«']:
                    misc['SpaceAfter'] = 'No'
                    if space_before:
                        text += ' '
                    text += wform
                elif i > 0 \
                 and wform in ['.', ',', ':', ';', '...',
                               '!', '?', '!..', '?..', "''", ')', '»']:
                    tokens[i - 1]['MISC']['SpaceAfter'] = 'No'
                    text += wform
                else:
                    if space_before:
                        text += ' '
                    text += wform
                space_before = misc.get('SpaceAfter') != 'No'
            sents_.append((tokens, text))
        return sents_

    def do_all(self, doc_id=None, **kwargs):
        """Make preprocessing (including tokenization) for the specified
        document

        :param doc_id: id of the document. If None then all the corpus 
                       will be processed
        :type doc_id: str

        Also, the function receives other parameters that fit for
        ``process_text()`` method"""
        assert doc_id is None or doc_id in self._corpus, \
            'ERROR: document "{}" has not exist'.format(doc_id)

        silent = kwargs.get('silent', False)
        if not silent:
            print('Preprocess corpus', file=LOG_FILE)
        corpus = self._corpus.values() if doc_id is None else \
                 [self._corpus[doc_id]]
        docs_cnt = len(corpus)
        pars_cnt = sents_cnt = tokens_cnt = 0
        for doc in corpus:
            tags = doc['tags'] = {}
            for par in doc.get('pars', []):
                sents = self.process_text(
                    par['text'], **kwargs, sent_no=sents_cnt, tags=tags
                )
                par['sents'] = []
                for tokens, text in sents:
                    par['sents'].append({'text': text, 'tokens': tokens})
                    tokens_cnt += len(tokens)
                sents_cnt += len(sents)
                pars_cnt += 1
        if not silent and sents_cnt >= 0:
            print_progress(sents_cnt, end_value=0, step=1000, file=LOG_FILE)
            print('Corpus has been processed: '
                  '{} documents, {} paragraphs, {} sentences, {} tokens'
                      .format(docs_cnt, pars_cnt, sents_cnt, tokens_cnt),
                  file=LOG_FILE)

    def save(self, path=None, doc_id=None, add_global_columns=False):
        """Save corpus to CoNLL-U format.

        :param path: path to the file to store result to. If you don't need to
                     store result on disk, keep it None
        :type path: str
        :param doc_id: id of the document. If None then all the corpus 
                       will be processed
        :type doc_id: str
        :param add_global_columns: if True, the first line of output will be
                                   CoNLL-U Plus "global.columns" metadata
        :return: the result of the processing
        :rtype: Parsed CoNLL-U
        """
        assert doc_id is None or doc_id in self._corpus, \
            'ERROR: document "{}" has not exist'.format(doc_id)
        sents = []
        for doc_id, doc in self._corpus.items() if doc_id is None else \
            [(doc_id, self._corpus[doc_id])]:
            assert 'pars' in doc, \
                   'ERROR: document {} does not have any data'.format(doc_id)
            for par_no, par in enumerate(doc['pars'], start=1):
                par_id = '{}-p{}'.format(doc_id, par_no)
                for sent_no, sent in enumerate(par['sents'], start=1):
                    sent_id = '{}-s{}'.format(par_id, sent_no)
                    tokens = sent['tokens']
                    meta = OrderedDict()
                    if par_no == 1 and sent_no == 1:
                        if add_global_columns:
                            meta['global.columns'] = \
                                'ID FORM LEMMA UPOS XPOS FEATS ' \
                                                   'HEAD DEPREL DEPS MISC'
                        meta['newdoc id'] = doc_id
                        meta.update(doc['meta'])
                    if sent_no == 1:
                        meta.update([('newpar id', par_id),
                                     ('par_text', par['text'])])
                    meta.update([('sent_id', sent_id), ('text', sent['text'])])
                    sents.append((tokens, meta))
        sents = Conllu.fix(sents, split_multi=True)
        if path:
            sents = list(sents)
            Conllu.save(sents, path, fix=False)
        return sents

    def unmask_tokens(self, corpus, save_to=None, keep_empty=True,
                      keep_tags=True, entity_map=None):
        """Replace masked tokens to their real values.

        :param corpus: path to CoNLL-U file or array of Parsed CoNLL-U
        :type corpus: str|Iterable
        :param save_to: path to the file to store result to. If you don't need
                        to store result on disk, keep it None
        :type save_to: str
        :param keep_empty: if True, entities with no replacement mask stay as
                           is
        :param keep_tags: if True, do not remove Toxine's tags from the MISC
                          field
        :param entity_map: add specified tags to the MISC field instead of
                           Toxine's tags
        :type entity_map: dict({<toxine tag>: tuple(<new tag>, <value>)})
        :return: the result of the processing
        :rtype: Parsed CoNLL-U
        """
        def process(corpus):
            if isinstance(corpus, str):
                corpus = Conllu.load(corpus)
            for sentence in corpus:
                for token in sentence[0] if isinstance(sentence, tuple) else \
                             sentence:
                    misc = token['MISC']
                    for tag, form in list(misc.items()):
                        tag_ = self.CHAR_DELIM + tag
                        if tag_ in self.TAG_MASKS:
                            subst = self.TAG_MASKS[tag_]
                            if subst or not keep_empty:
                                token['FORM'] = form
                            if not keep_tags:
                                misc.pop(tag)
                            if entity_map:
                                subst = entity_map.get(tag)
                                if subst:
                                    misc.update(subst if isinstance(subst,
                                                                    dict) else
                                                [subst])
                            break
                yield sentence

        corpus = process(corpus)

        if save_to:
            Conllu.save(corpus, save_to, fix=False)
            corpus = Conllu.load(save_to)
        return corpus
