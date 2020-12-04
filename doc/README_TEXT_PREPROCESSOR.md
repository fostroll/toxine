<div align="right"><strong>RuMor: Russian Morphology project</strong></div>
<h2 align="center">Toxine: a tiny python NLP library for Russian text preprocessing</h2>

## Text tokenization and preprocessing tools

The class `TextPreprocessor` contains a lot of bells and whistles for
organizing text preprocessing pipeline. It takes a simple text that may be
highly noisy, and returns its cleaned tokenized version in
[*CoNLL-U*](https://universaldependencies.org/format.html) format.

To create `TextPreprocessor`, invoke:
```python
from toxine import TextPreprocessor
tp = TextPreprocessor()
```

If you have some
[*Corpus Dictionary*](https://github.com/fostroll/corpuscula/blob/master/doc/README_CDICT.md)
saved, you may use it with `TextPreprocessor` as helper:
```python
tp = TextPreprocessor(cdict_restore_from='cdict.pickle')
```

Also, you can create (and save, if you'll specify **save_to** param) *Corpus
Dictionary* for `TextPreprocessor` from any *CoNLL-U* corpus you prefer.
E.g., you can use `TextPreprocessor` with *SynTagRus*:
```python
from corpuscula.corpus_utils import syntagrus
tp = TextPreprocessor(cdict_corpus=syntagrus, save_to='cdict.pickle')
```

**NB:** Do not use *OpenCorpora* as the source for *Corpus Dictionary* helper,
because we use it already via
[*pymorphy2*](https://pymorphy2.readthedocs.io/en/latest/).

### Loading. Documents and Paragraphs

First of all, you need load documents you want to preprocess. Usually, you'll
use for that the `load_pars()` method:
```python
tp.load_pars(path, encoding='utf-8-sig', eop=r'\n', doc_id=None)
```
Here, you should specify **path** to a text file you want to process. For
each loaded file `TextPreprocessor` creates a separate *document* unless you
specify **doc_id**. The *document* will be filled by *paragraphs* extracted
from the file by applying **eop** param.

**eop** is a regex or a `callable` for splitting a text. If `None`, then all
the texts will be placed into one *paragraph*. Default is *LF* symbol.

**doc_id** is the *ID* of the *document* that you want to append. Usually, you
don't need it. You just feed your file(s) to `TextPreprocessor` and save the
result to one *CoNLL-U* file in the feeding order. In that case, each file
will be tagged as separated *document*, and you have no reason to keep *ID* of
them. But if you want some additional functionality (append *documents*, for
example, or save them to different files), you must firstly create each
*document* directly:
```python
doc_id = tp.new_doc(self, doc_id=None, metadata=None)
```
Param **metadata** allows you to specify *CoNLL-U* *metadata* that will be
inserted to the document header. **metadata** must be of `OrderedDict` type
as you can see in
[*Parsed CoNLL-U*](https://github.com/fostroll/corpuscula/blob/master/doc/README_PARSED_CONLLU.md)
description.

If you know *ID*, you can remove a certain *document*:
```python
tp.remove_doc(doc_id)
```

You don't need *ID* if you need to clear the whole corpus:
```python
tp.clear_corpus()
```

### Additional tools for loading

If you already have your *paragraphs* in memory as text (tokenized or not),
you can load them by means of
```
tp.new_par(text, doc_id=None)
```
if the **text** is the whole paragraph.

Or, if your data contains several *paragraphs*, load it via
```
tp.new_pars(pars, eop=r'\n', doc_id=None)
```
Here, **pars** may be either a text data or a `list` of already splitted
*paragraphs*. In the latter case, param **eop** is ignored.

If you want full control, you can just split your text first:
```
pars = TextPreprocessor.text_to_pars(text, eop=r'\n')
```
Next, you can check and edit the result of splitting, and then load it via
`tp.new_pars(pars)`.

### Preprocessing

Normally, you will use only one method that makes all the work: `do_all()`.
However, this method has a lot of parameters to control its behavior:
```python
tp.do_all(doc_id=None, chars_allowed=None, unescape_html=True, pre_tag=None,
          tag_emoji=True, tag_xml=True, tag_email=True, tag_uri=True,
          tag_phone=True, tag_date=True, tag_hashtag=True, tag_nametag=True,
          post_tag=None, split_unk=False, tag_unk=True, norm_punct=False,
          islf_eos=True, istab_eos=True, ignore_case=False, silent=False,
          sent_no=0, tags={})
```
The method executes all preprocessing including sentence and word tokenization,
normalizing punctuation (if needed), extracting some entities detected via
regexes, etc.

If **doc_id** is specified, metod affects only the *document* with that
*ID*. Elsewise, all the corpus will be processed.

**chars_allowed**: charset considered valid. Tokens with others characters will
be processed as *UNK* tokens. By default, **chars_allowed** contains the following
character set: **$€%&~№0-9A-Za-zЁА-Яёа-я’²³°()/"\'«»„“+.,:;!?-**. You can change or replace
it by any other chatset placed inside `[]` regex.

**unescape_html**: do we need to make back transformation from escaped html.
May be `True` (default), `False` or `callable`. The signature of the
`callable` for this method: `unescape_html(text: str) -> str`.

**pre_tag**: external tagger (or just a preprocessor) that will be run before
all internal taggers. The signature: `pre_tag(text: str, delim: str) -> str`.
Here, `delim` is a character to separate tag signature. For example, if we've
got `'|'` as `delim` and we want to tag all numbers, then for the `text` *'I
have 8 brothers and only one sister'* we should return smth like *'I have
**8|EntityNumber** brothers and only **one|EntityNumber** sister'*. Default
value is `None`: we don't need external preprocessing.

**tag_emoji**, **tag_xml**, **tag_email**, **tag_uri**, **tag_phone**,
**tag_date**, **tag_hashtag**, **tag_nametag**. Internal preprocessors that we
have. They will be started exactly in that order. Each of the params can be
either `True` (default: run the preprocessor), `False` (do not run the 
preprocessor) or `callable`: we want to run our external preprocessor instead.
In the latter case, the signature of your callback function is the same as for
**pre_tag**.

**post_tag**: external tagger we want to run after all internal taggers. It is
the same as for **pre_tag**. Default is `None` (we don't need it).

**split_unk**: if unallowed chars are met only at the beginning or/and at the end
of the token then split that token and mark as *UNK* only the part with
unallowed characters. Default is `False`.

**tag_unk**: add a special tag for the tokens with unallowed chars. Default is
`True`, i.e. tokens will be tagged. If `False`, that tokens will be silently
removed from the text.

**norm_punct**: normalize punctuation. It's not a *correction*, it's just
*normalizing*, i.e. reduction of user's punctuation to some appropriate form with
finite variants of punctiation uses. It is not necessary to use this methos if the
text source already has a good grammar (*Wikipedia*, newspapers, etc.). But
if your text is punctuation-dirty (texts from social networks, chats or forums), 
the method is useful. Default is `False`. You can't replace it with your `callable`. 
If needed, you can do your normalizing in the **post_tag** method.

If **norm_punct** is `True`, you can specify some additional params for it:

**islf_eos**: if `True` (default), the *LF* symbol marks end of sentence and
will be replaced to `'.'`.

**istab_eos** if `True` (default), the *TAB* symbol marks end of sentence and
will be replaced to `'.'`.

**ignore_case**: if `True`, do not consider character case during punctuation
processing. Use it, if your text is case-ignorant. Default is `False`.

Next params are used regardless of **norm_punct**:

**silent** (`True` / `False` (default)): suppress log.

**sent_no** (`int`, default is `0`): init value for the progress indicator
(has effect if silent is `False`)

**tags**: (`dict(tag, value)`) storage for the tags found. Sometimes, you want
to split your corpus in several parts (because of large size, for example) and
process each part independently. With that, you want to get consistent
numeration of found tags for the whole corpus. In that case, just create an
empty `dict` and pass it to this method with every call. Each time the method
will continue preceding numerations.

### External taggers implementation

If you want to have your own tags to be supported (for you could use them in
**pre_tag** and/or **post_tag**), you should register them first:
```python
eff_tag = tp.register_tag(tag, mask=None)
```
Here, **tag** is the signature for your tag that will be placed to the *MISC*
*CoNLL-U* field as follows. E.g. you want to mark some tokens as *EntityYear*.
Then, you should firstly register the *EntityYear* tag:
```python
eff_tag = tp.register_tag('EntityYear', mask='year')
```
The **mask** param allows to specify a substitute that will be placed to the
processing text instead of tokens found. If **mask** is `None` (default), they
will be replaced to `None`.

Thus, if your **pre_tag** or **post_tag** were embodied correctly, method
`do_all()` will convert the clause *"Это случилось в 1887-м году."* into:
```sh
1	Это	[...]	-
2	случилось	[...]	-
3	в	[...]	-
4	год	[...]	EntityYear=1987|SpaceAfter=No
5	.	[...]	-
```

The example of using **post_tag** param in `do_all` method along with new tags
definition can be found in the `examples` directory of the ***Toxine*** github
repository (script `tokenize_post_tag.py`).

If necessary, the `register_tag()` method allows you to redefine **masks** of
internal tags. E.g.:
```python
tp.register_tag('EntityPhone', 'телефон')
```

All current **mask** mappings are kept in `tp.TAG_MASKS` dictionary, but the
tags there are represented in the form already adjusted for our pipeline. Better
don't edit it directly.

### Saving the result

After processing, you can save the results:
```python
sents = tp.save(path=None, doc_id=None, add_global_columns=False)
```
Use **doc_id** if you want to get only one certain document preprocessed.
Otherwise, the method will return all of them.

The result is returned in *Parsed CoNLL-U* format. If you set
**add_global_columns** to `True`, the meta variable *global.columns* will be
added to the result to make it consistent with the
[*CoNLL-U Plus*](https://universaldependencies.org/format.html) format.

To save the result as *CoNLL-U* file, just specify the name of the resulting
file in the **path** param.

### Restore original tokens

After corpus has been processed (e.g., morphological parsing was made), you
can return early substituted tokens to their original places.
```python
sents = tp.unmask_tokens(corpus, save_to=None, keep_empty=True,
                         keep_tags=True, entity_map=None):
```
Here, **corpus** is a name of the file in *CoNLL-U* format or a list/iterator
of sentences in *Parsed CoNLL-U*.

The result is returned in *Parsed CoNLL-U* format. To save the result as
*CoNLL-U* file, just specify the name of the resulting file in the **save_to**
param.

If **keep_empty** is `True` (default), entities with no replacement mask stay
as is.

if **keep_tags**: is `True`, we won't remove ***Toxine***'s tags from the
*MISC* field.

Also, there is possibility to add new tags to the *MISC* field based on
***Toxine***'s tags. For that purpose **entity_map** param is used. It contain
a `dict` of mappings, e.g.:
`{'EntityDate': ('NE', 'Date'), 'EntityPhone': ('NE', 'Phone')}`

### Supplements

If you have a text piece in some variable and you need to just preprocess and
tokenize it without any additional text processing, you can do it in one
line like this:
```python
sents = tp.process_text(text, **kwargs)
```
You'll get a `list` of sentences in *Parsed CoNLL-U* format, but its
*metadata* will contain only *text* meta variables.

The **\*\*kwargs** params is exactly params of the `do_all()` method except
**doct_id** (you have param **text** instead).

**NB:** you have to create the instance of `TextPreprocessor`. The method
`process_text` is not static.

Normalizing punctuation can also be done without full text processing:
```python
text = tp.norm_punct(text, islf_eos=True, istab_eos=True, ignore_case=False)
```

The `norm_punct` method is non-static, too. All its params were explained
above.

### Tokenization

We have static methods for sents and words tokenization:
```python
sents = TextPreprocessor.sent_tokenize(text, kill_empty=True)
tokens = TextPreprocessor.word_tokenize(text)
```
Hovewer, now, both of them are simple wrappers for *NLTK* methods of same
name, because after preprocessing they work pretty well.

Param **kill_empty** allows you not to add empty sentences to the return.

Also, we have a wrapper that makes all tokenization at once:
```python
tokens = TextPreprocessor.tokenize(text, kill_empty=True)
```
