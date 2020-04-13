<div align="right"><strong>RuMor: Russian Morphology project</strong></div>
<h2 align="center">Toxic: a tiny python NLP library for Russian text preprocessing</h2>

## Text tokenization and preprocessin tools

The class `TextPreprocessor` contains a lot of bells and whistles for
organizing text preprocessing pipeline. It takes a simple text that may be
highly dirty, and return it's cleaned tokenized version in
[*CONLL-U*](https://universaldependencies.org/format.html) format.

To create `TextPreprocessor`, invoke:
```python
from toxic import TextPreprocessor
tp = TextPreprocessor()
```

If you have some
[*Corpus Dictionary*](https://github.com/fostroll/corpuscula/blob/master/doc/README_CDICT.md)
saved, you may use it with `TextPreprocessor` as helper:
```python
tp = TextPreprocessor(cdict_restore_from='cdict.pickle')
```

Also, you can create (and save, if you'll specify **save_to** param) *Corpus
Dictionary* for `TextPreprocessor` from any *CONLL-U* corpus you prefer.
E.g., you can use `TextPreprocessor` with *SynTagRus*:
```python
from corpuscula.corpus_utils import syntagrus
tp = TextPreprocessor(cdict_corpus=syntagrus, save_to='cdict.pickle')
```

**NB:** Do not use *OpenCorpora* as the source for *Corpus Dictionary* helper,
because we use it in any case via
[*pymorphy2*](https://pymorphy2.readthedocs.io/en/latest/).

### Loading. Documents and Paragraphs

First of all, you need load documents you want to preprocess. Usually, you'll
use for that the `load_pars()` method:
```python
tp.load_pars(path, encoding='utf-8-sig', eop=r'\n', doc_id=None)
```
Here, you should specify **path** to a text file you want to process. For
each loaded file `TextPreprocessor` creates separate *document* unless you
specify **doc_id**. That document will be filled by *paragraphs* extracted
from the file by applying **eop** param.

**eop** is a regex or callback function for splitting a text. If None then all
the text will be placed into one paragraph. Default is *LF* symbol.

**doc_id** is the *ID* of the *document* you want to be appended. Usually, you
don't need it. You just feed your file(s) to `TextPreprocessor` and save the
result to one *CONLL-U* file in the feeding order. In that case, each file
will be tagged as separated *document*, and you have no reason to keep *ID* of
them. But if you want some additional functionality (append documents, for
example, or save them to different files), you must firstly create each
*document* directly:
```python
doc_id = tp.new_doc(self, doc_id=None, metadata=None)
```
Param **metadata** allows you to specify *CONLL-U* metadata that will be
inserted to the document header. **metadata** must be of `OrderedDict` type
as you can see in
[*Parsed CONLL-U*](https://github.com/fostroll/corpuscula/blob/master/doc/README_PARSED_CONLLU.md)
description.

If you know *ID*, you can remove a certain document:
```python
tp.remove_doc(doc_id)
```

You don't need *ID* if you need to clear the whole corpus:
```python
tp.clear_corpus()
```

### Additional tools for loading

If you already have your *paragraphs* in memory as text (tokenized or not),
you can load them by means
```
tp.new_par(text, doc_id=None)
```
if the **text** is the whole paragraph

or, if your data contain several *paragraphs*, load it via
```
tp.new_pars(pars, eop=r'\n', doc_id=None)
```
Here, **pars** may be either a text data or a list of already splitted
*paragraphs*. In the latter case param **eop** is ignored.

If you want full control, you can firstly just split your text:
```
pars = TextPreprocessor.text_to_pars(text, eop=r'\n')
```
Next, you can check and edit the result of splitting, and then load it via
`tp.new_pars(pars)`.

### Preprocessing

Normally, you will use the only one method that makes all work: `do_all()`.
However, that method have a lot of parameters that control its behavior:
```python
tp.do_all(doc_id=None, chars_allowed=None, unescape_html=True, pre_tag=None,
          tag_emoji=True, tag_xml=True, tag_email=True, tag_uri=True,
          tag_phone=True, tag_date=True, tag_hashtag=True, tag_nametag=True,
          post_tag=None, split_unk=False, tag_unk=True, norm_punct=False,
          islf_eos=True, istab_eos=True, ignore_case=False, silent=False,
          sent_no=0, tags={})
```
This metod execute all preprocessing including sentence and word tokenization,
normalizing of punctuation (if need), extracting some entities detected via
regex etc.

If **doc_id** is specified, metod affects only on the *document* with that
*ID*. Elsewise, all the corpus will be processed.

**chars_allowed**: charset we mean valid. Tokens with others characters will
be processed as *UNK* tokens. By default, **chars_allowed** contain character
set: **$€%&~№0-9A-Za-zЁА-Яёа-я’²³°()/"\'«»„“+.,:;!?-**. You can change it by
any other set that can be plased inside `[]` regex.

**unescape_html**: do we need to make back transformation from escaped html.
May be `True` (default), `False` or `callable`. The signature of the
`callable` for this method: `unescape_html(text: str) -> str`.

**pre_tag**: external tagger (or just preprocessor) that will be run before
all internal taggers. The signature: `pre_tag(text: str, delim: str) -> str`.
`delim` here is a character to separate tag signature. For example, if we've
got `'|'` as `delim` and want to tag all numbers, then for the `text` *'I
have 8 brothers and only one sister'* we should return smth like *'I have
8|Number brothers and only one|Number sister'*. Default value is `None`: we
don't need external preprocessing.

**tag_emoji**, **tag_xml**, **tag_email**, **tag_uri**, **tag_phone**,
**tag_date**, **tag_hashtag**, **tag_nametag**. Internal preprocessors that we
have. They will be started exactly in that order. Each of the param can be
either `True` (default: we want preprocessor to be runned), `False` (we don't
want that) or `callable` if we want to run our external preprocessor instead.
In the latter case the signature of your callback function is the same as for
**pre_tag**.

**post_tag**: external tagger we want to run after all internal taggers. The
is the same as for **pre_tag**. Default is `None` (we don't need it).

**split_unk**: if disallowed chars placed only at the begin or/and at the end
of the token then split that token and mark as *UNK* only part with disallowed
characters. Default is `False`.

**tag_unk**: add special tag for the tokens with disallowed chars. Default is
`True`, i.e. tokens will be tagged. If `False`, that tokens will be silently
removed from the text.

**norm_punct**: normalize punctuations. It's not a *correction*, it's just
*normalizing*, i.e. reduction user's punctuation to some appropriate form with
finite variants of punctiation uses. You won't apply this possibility if the
text sourse has already good grammar (*Wikipedia*, news papers, etc.). But
if your text is punctuation dirty (chats' of forums' talks), the method is
usefull. Default is `False`. You can't replace it with your `callable`. If you
need, you can do your normalizing in the **post_tag** method.

If **norm_punct** is `True` you can specify some additional params for it:

**islf_eos**: the *LF* symbol marks end of sentence and will be replaced to
`'.'`.

**istab_eos** the *TAB* symbol marks end of sentence and will be replaced to
`'.'`.

**ignore_case**: do not consider character case during punctuation processing.
Use it, if your text is case-ignorant.

Next params are used regardless of **norm_punct**:

**silent** (`True` / `False` (default)): suppress log.

**sent_no** (`int`, default is `0`): init value for the progress indicator
(has meaning if silent is not `False`)

**tags**: (`dict(tag, value)`) storage for the tags found. Sometimes, you want
to split your corpus by several parts (because of size, for example), and
process each part independently. With that, you want to get consistent
numeration of founded tags for the all corpus. In that case, just create an
empty `dict` and pass it to this method with every call. The method will
continue preceding numerations.

### External taggers implementation

If you want to have your own tags to be supported (for that you can use them
in **pre_tag** and/or **post_tag**), you should to register them first:
```python
eff_tag = tp.register_tag(tag, mask=None)
```
Here, **tag** is the signature for for your tag that will be placed to the
*MISC* *CONLL-U* field as follows. E.g. you want to mark some tokens as
*EntityYear*. Then, you should firstly to register the *EntityYear* tag:
```python
eff_tag = tp.register_tag('EntityYear', mask='year')
```
The **mask** param allows to specify a substitute that will be placed to the
processing text instead of tokens found. If **mask** is `None` (default), they
will be replaced to `None`.

Thus, if your **pre_tag** or **post_tag** was embodied correctly, the clause
like *"Это случилось в 1887-м году."* will be converted after `do_all()` to:
```sh
1	Это	[...]	-
2	случилось	[...]	-
3	в	[...]	-
4	год	[...]	EntityYear=1987
5	.	[...]	-
```

The example of usage **post_tag** param in `do_all` method along with new tags
definition you can find in the `examples` directory of the ***Toxic*** github
repository (script `tokenize_post_tag.py`).

If you want, with the `register_tag()` method you can redefine **masks** of
internal tags. E.g.:
```python
tp.register_tag('EntityPhone', 'телефон')
```

All current **mask** mappings keeps in `tp.TAG_MASKS` dictionary but the tags
there keeps in the form already adjusted for our pipeline. Better don't edit
it directly.

### Saving the result

After processing, you'd like to get the result:
```python
sents = tp.save(path=None, doc_id=None, add_global_columns=False)
```
Use **doc_id** if you want to get only one certain document preprocessed.
Otherwise, the method will return all of them.

The result is returned in
[*Parsed CONLL-U*](https://github.com/fostroll/corpuscula/blob/master/doc/README_PARSED_CONLLU.md)
format. If you set **add_global_columns** to `True`, the meta variable
*global.columns* will be added to the result for make it consistent with
[*CONLL-U Plus*](https://universaldependencies.org/format.html).

To save the result as *CONLL-U* file, just specify the name of the resulting
file in the **path** param.

### Supplements

If you have a text piece in some variable, and you need just to preprocess and
tokenize it without any addition document processing, you can do it in one
line like this:
```python
sents = TextPreprocessor().process_text(text, **kwargs)
```
You'll get a `list` of sentences in *Parsed CONLL-U* format, but its
*metadata* will contain only *text* meta variables.

The **\*\*kwargs** params is exactly params of `do_all()` except you can't use
**doct_id** here (you have param **text** instead).

**NB:** we have to create the instance of `TextPreprocessor`. The method
`process_text` is not static.

Normalizing punctuation also can be done without full processing via:
```python
text = TextPreprocessor().norm_punct(text, islf_eos=True, istab_eos=True,
                                     ignore_case=False)
```

The `norm_punct` method is non-static, too. All its params were explained
above.

### Tokenization

We have static methods for sents and words tokenization:
```python
sents = TextPreprocessor.sent_tokenize(text, kill_empty=True)
tokens = TextPreprocessor.word_tokenize(text)
```
But now, both of them are simple wrappers for *NLTK* methods of same name,
because after preprocessing they works pretty well.

Param **kill_empty** allow you not to add to the return empty sentences.

Also, we have a wrapper that makes all tokenization at once:
```python
sents = TextPreprocessor.sent_tokenize(text, kill_empty=True)
tokens = TextPreprocessor.tokenize(text, kill_empty=True)
```
