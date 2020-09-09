<div align="right"><strong>RuMor: Russian Morphology project</strong></div>
<h2 align="center">Toxine: a tiny python NLP library for Russian text preprocessing</h2>

[![PyPI Version](https://img.shields.io/pypi/v/toxine?color=blue)](https://pypi.org/project/toxine/)
[![Python Version](https://img.shields.io/pypi/pyversions/toxine?color=blue)](https://www.python.org/)
[![License: BSD-3](https://img.shields.io/badge/License-BSD-brightgreen.svg)](https://opensource.org/licenses/BSD-3-Clause)

A part of ***RuMor*** project. It contains pipeline for preprocessing and
tokenization texts in *Russian*. Also, it includes preliminary entity tagging.
Highlights are:

* Extracting emojis, emails, dates, phones, urls, html/xml fragments etc.
* Tagging/removing tokens with unallowed symbols
* Normalizing punctuation
* Tokenization (via *NLTK*)
* Russan *Wikipedia* tokenizer
* [*brat*](https://brat.nlplab.org/) annotations support

## Installation

### pip

***Toxine*** supports *Python 3.5* or later. To install it via *pip*, run:
```sh
$ pip install toxine
```

If you currently have a previous version of ***Toxine*** installed, use:
```sh
$ pip install toxine -U
```

### From Source

Alternatively, you can also install ***Toxine*** from source of this *git
repository*:
```sh
$ git clone https://github.com/fostroll/toxine.git
$ cd toxine
$ pip install -e .
```
This gives you access to examples that are not included to the *PyPI* package.

## Setup

***Toxine*** uses *NLTK* with *punkt* data downloaded. If you didn't do it yet,
start *Python* interpreter and execute:
```python
>>> import nltk
>>> nltk.download('punkt')
```

## Usage

[Text Preprocessor](https://github.com/fostroll/toxine/blob/master/doc/README_TEXT_PREPROCESSOR.md)

[Wrapper for tokenized *Wikipedia*](https://github.com/fostroll/toxine/blob/master/doc/README_WIKIPEDIA.md)

[*brat* annotations support](https://github.com/fostroll/toxine/blob/master/doc/README_BRAT.md)

## Examples

You can find them in the directory `examples` of our ***Toxine*** github
repository.

## License

***Toxine*** is released under the BSD License. See the
[LICENSE](https://github.com/fostroll/toxine/blob/master/LICENSE) file for
more details.
