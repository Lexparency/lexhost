"""
Definition of analyzers per language and index settings.
"""
from collections import namedtuple
from elasticsearch_dsl import token_filter, analyzer

__all__ = ['numbers', 'create_analysis']

numbers = {
    "number_of_shards": 5,
    "number_of_replicas": 2
}


StopStem = namedtuple('StopStem', ['stop', 'stem'])


_filters = {
    'de': StopStem(
        token_filter(
            'german_stop',
            type='stop',
            stopwords="_german_"
        ),
        token_filter(
            'german_stemmer',
            type='stemmer',
            language="light_german"
        )
    ),
    'es': StopStem(
        token_filter(
            'spanish_stop',
            type='stop',
            stopwords="_spanish_"
        ),
        token_filter(
            'spanish_stemmer',
            type='stemmer',
            language="light_spanish"
        )
    ),
    'en': StopStem(
        token_filter(
            'english_stop',
            type='stop',
            stopwords="_english_"
        ),
        "porter_stem"
    )
}


def create_analysis(language) -> analyzer:
    language = language.lower()
    if language not in _filters.keys():
        raise NotImplemented("Sorry, language {} not yet available")
    f = _filters[language]
    return analyzer(
        'analyzer_{}'.format(language),
        char_filter=["html_strip"],
        tokenizer="standard",
        filter=[
            "lowercase",
            "asciifolding",
            f.stop,
            f.stem
        ]
    )

