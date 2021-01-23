<div align="right"><strong>RuMor: Russian Morphology project</strong></div>
<h2 align="center">Toxine: a tiny python NLP library for Russian text preprocessing</h2>

## *brat* annotations support

[*brat*](https://brat.nlplab.org/) is a popular tool that is often used to
annotate texts. It allows annotate raw untokenized text blocks. Thus, it
doesn't care of the borders of tokens. By default, we move borders of the
annotations to the borders of tokens, so user don't have to be very accurate
during text labeling.

***Toxine*** supports all *brat* annotations. Also, we provide a possibility
to convert *brat* entity labels (type "T") to MISC:NE labels that are used by 
[***MorDL***](https://github.com/fostroll/mordl) package to keep named
entities.

A standard way to convert *brat* filles to
[*CoNLL-U Plus*](https://universaldependencies.org/format.html) format is like
that:
```python
from toxine.brat import brat_to_conllu
brat_to_conllu(txt_fn, ann_fn=None, save_to=None, keep_tokens=True,
               make_ne=False, keep_originals=True, cdict_path=None,
               **kwargs)
```

Params **txt_fn**, **ann_fn** are paths to the *brat* `txt` and `ann` files.
If **ann_fn** is `None` (default), an extension of **txt_fn** file will be
changed to `.ann`.

Param **save_to** is a path where result will be stored. If not specified,
the function returns the result as a generator of
[*Parsed CoNLL-U*](https://github.com/fostroll/corpuscula/blob/master/doc/README_PARSED_CONLLU.md)
data.

If param **keep_tokens** is `True` (default), the function adjusts borders
of annotations to the borders of text tokens. If `False`, the borders are left
as is, so some tokens may be splitted.

If param **make_ne** is ``True``, *brat* "T" entities will convert to MISC:NE
entities supported by ***MorDL***. Note, that if several *brat* "T" entities
are linked to the one token, only first one will be used (it is allowed only
one MISC:NE entity for the token). Default ``False``.

Param **keep_originals** is relevant with **make_ne** = `True`. If
**keep_originals** is `True` (default), original MISC:bratT entities will be
stayed intact. Elsewise, they will be removed.

Param **cdict_path** (optional) allow to specify a path to the
***Corpuscula***'s corpus dictionary backup file. If you don't have it, don't
worry about it.

Also, the function receives other parameters that fit for ***Toxine***'s
`TextPreprocessor.do_all()` method.

**Note** that after you've had the result in *CoNNL-U* format, you may want to
merge it with some other annotations of the same corpus. For achieve that, use
methods from
[***Corpuscula*** library](https://github.com/fostroll/corpuscula/blob/master/doc/README_CDICT.md)
to merge *CoNLL-U* files:
```python
from corpuscula import Conllu
Conllu.save(Conllu.merge('file1.conllu', 'file2.conllu', stop_on_error=False,
                         log_file=None),
            'result.conllu')
```

To create *brat* files from *CoNLL-U* to annotate, use:
```python
conllu_to_brat(corpus, txt_fn, ann_fn=None, spaces=1)
```
Here, **corpus** is either a file in *CoNNL-U* or data in *Parsed CoNLL-U*
format.

Params **txt_fn**, **ann_fn** are paths to the *brat* `txt` and `ann` files.
If **ann_fn** is `None` (default), an extension of **txt_fn** file will be
changed to `.ann`.

**spaces** is a number of spaces to use as word delimiter.

Note, that we create empty `.ann` files. Use the function to get initial data
for annotation.

---
Other methods of the package are useful if you want to execute stages of the
above process separately.

```python
from toxine.brat import embed_brat_text_bound_annotations
embed_brat_text_bound_annotations(txt_fn, ann_fn, save_to=None,
                                  keep_tokens=True)
```
Converts `txt` and `ann` *brat* files to the text file with embedded
annotations.

Params **txt_fn**, **ann_fn** are paths to the *brat* `txt` and `ann` files.

Param **save_to** is a path where result will be stored. If not specified, the
function returns the result as a generator of text data.

If param **keep_tokens** is `True` (default), the function adjusts borders
of annotations to the borders of text tokens. If `False`, the borders are left
as is, so some tokens may be splitted.

```python
from toxine.brat import postprocess_brat_conllu
postprocess_brat_conllu(corpus, save_to=None)
```
Does postprocessing for the **corpus** with embedded brat annotations
which already was preliminarily prepared by ***Toxine***'s `TextPreprocessor`.

Param **save_to** is a path where result will be stored. If not specified, the
function returns the result as a generator of *Parsed CoNLL-U* data.

```python
from toxine.brat import make_ne_tags
make_ne_tags(corpus, save_to=None, keep_originals=True)
```
Process the **corpus** in *CoNLL-U* or *Parsed CoNLL-U* format such that
MISC:bratT entities converts to MISC:NE entities supported by MorDL. Note,
that if several bratT entities are linked to the one token, only first one
will be used (it is allowed only one MISC:NE entity for the token).

Param **save_to** is a path where result will be stored. If not specified, the
function returns the result as a generator of *Parsed CoNLL-U* data.

If param **keep_originals** is `True` (default), original MISC:bratT entities
will be stayed intact. Elsewise, they will be removed.
