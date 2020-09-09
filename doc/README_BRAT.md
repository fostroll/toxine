<div align="right"><strong>RuMor: Russian Morphology project</strong></div>
<h2 align="center">Toxine: a tiny python NLP library for Russian text preprocessing</h2>

## *brat* annotations support

[*brat*](https://brat.nlplab.org/) is a popular tool that is often used to
label named entities. It allows annotate raw untokenized text blocks. Thus, it
doesn't care of the borders of tokens. By default, we move borders of the
annotations to the borders of tokens, so user don't have to be very accurate
during text labeling.

Now, ***Toxine*** supports only text-bound annotations that are usually used
for the labeling named entities and some similar purposes. Also, we provide
a possibility to convert *brat* labels to MISC:NE labels that are used by 
[***Mordl***](https://github.com/fostroll/mordl) package to keep named
entities.

A standard way to convert *brat* labels to MISC:NE is just invoke:
```python
from toxine.brat import brat_to_ne
brat_to_ne(txt_fn, ann_fn, save_to=None, split_tokens=False, cdict_path=None)
```

Params **txt_fn**, **ann_fn** are paths to the *brat* `txt` and `ann` files.

Param **save_to** is a path where the result will be stored. If not specified,
the function returns the result as a generator of
[*Parsed CoNLL-U*](https://github.com/fostroll/corpuscula/blob/master/doc/README_PARSED_CONLLU.md)
data.

If param **split_tokens** is `False` (default), the function adjusts borders
of annotations to the borders of text tokens. Otherwise, tokens will be
splitted if borders of annotations don't fit with corresponding borders of
tokens.

Param **cdict_path** (optional) allow to specify a path to the
***Corpuscula***'s corpus dictionary backup file. If you don't have it, don't
worry about it.

**Note**, that if several brat entities are linked to the one token, all
except the first one will be ignored.

Other methods of the package are useful if you want to execute stages of the
above process separately.

```python
from toxine.brat import add_brat_text_bound_annotations
add_brat_text_bound_annotations(txt_fn, ann_fn, save_to=None,
                                split_tokens=False)
```
Converts `txt` and `ann` *brat* files to the text file with embedded
annotations.

Params **txt_fn**, **ann_fn** are paths to the *brat* `txt` and `ann` files.

Param **save_to** is a path where the result will be stored. If not specified,
the function returns the result as a generator of text data.

If param **split_tokens** is `False` (default), the function adjusts borders
of annotations to the borders of text tokens. Otherwise, tokens will be
splitted if borders of annotations don't fit with corresponding borders of
tokens.

```python
def postprocess_brat_conllu(corpus, save_to=None)
```
Converts **corpus** in text format into *CoNLL-U* format. Embedded *brat*
entities will be placed to the MISC field.

Param **save_to** is a path where the result will be stored. If not specified,
the function returns the result as a generator of *Parsed CoNLL-U* data.

```python
def make_ne_tags(corpus, save_to=None)
```
Replaces *brat* entities in the **corpus** in *CoNLL-U* or *Parsed CoNLL-U*
format to MISC:NE entities supported by ***Mordl***. Note, that if several brat
entities are linked to the one token, only first one will be used.

Param **save_to** is a path where the result will be stored. If not specified,
the function returns the result as a generator of *Parsed CoNLL-U* data.
