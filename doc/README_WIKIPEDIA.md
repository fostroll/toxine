<div align="right"><strong>RuMor: Russian Morphology project</strong></div>
<h2 align="center">Toxine: a tiny python NLP library for Russian text preprocessing</h2>

## Wrapper for tokenized *Wikipedia*

The package `wikipedia_utils` contains tools to simplify *Wikipedia* usage in
NLP tasks. So far, ***Toxine*** promotes only preprocessing for texts in
Russian. Thus, it supports only Russian part of *Wikipedia*.

```python
from toxine.wikipedia_utils import TokenizedWikipedia
TokenizedWikipedia.articles()
```
The method return articles in
[*Parsed CONLL-U*](https://github.com/fostroll/corpuscula/blob/master/doc/README_PARSED_CONLLU.md)
format, that can be saved to
[CONLL-U](https://universaldependencies.org/format.html) file with:
```python
from corpuscula import Conllu
Conllu.save(TokenizedWikipedia().articles(), 'wiki.conllu', fix=False,
            log_file=None)
```

The wrapper is successor of
[***Corpuscula*** *Wikipedia* Wrapper](https://github.com/fostroll/corpuscula/blob/master/doc/README_WIKIPEDIA.md),
so it supports its other methods (`titles()` and `templates()`) as well. But
they stay as they were, without any additional processing.

If you need your *Wikipedia* dump to blend in with some speech recognition
software output, please use 
[***Corpuscula***](https://github.com/fostroll/corpuscula) functionality:
```python
from corpuscula import Conllu
Conllu.save(TokenizedWikipedia().articles(), 'wiki_speech.conllu', fix=True,
            adjust_for_speech=True, log_file=None)
```
