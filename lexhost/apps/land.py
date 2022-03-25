from datetime import timedelta

from django.shortcuts import render, redirect
from elasticsearch import NotFoundError
from django.http import QueryDict
from django_http_exceptions import HTTPExceptions

from legislative_act.provider import DocumentProvider
from legislative_act.searcher import CorpusSearcher
from legislative_act.utils.generics import get_today

from .bot_api import LatestHistories
from .read import Diamonds
from .search import SearchForm
from ..settings import FEATURED, LANGUAGE_DOMAIN
from ..standard_messages import standard_messages


def get_featured(domain: str, ids_local: tuple):

    def get_display(title, acronym):
        if title is not None and acronym is not None:
            return f'{title} ({acronym})'
        return title or acronym

    result = []
    for id_local in ids_local:
        try:
            dp = DocumentProvider(domain, id_local)
        except NotFoundError:
            continue
        if not dp.current_is_available:
            continue
        cover = dp.get_cover('initial')
        display = get_display(cover.pop_title, cover.pop_acronym)
        if display is None:
            continue
        result.append({
            'id_local': id_local,
            'document_id': Diamonds().get_alias(id_local),
            'title': display
        })
    return result


def get_covid():
    query = SearchForm.parse(QueryDict('search_words=COVID'))
    hits = CorpusSearcher(query['search_words'], query.as_filter()) \
        .get_page(1)['hits']
    return [{'href': h['href'], 'title': h['title']} for h in hits]


def get_recents():

    def refine(doc_hit: dict):
        transaction_types = set(item['transaction_type']
                                for item in doc_hit.pop('body'))
        if transaction_types == {'insert'}:
            doc_hit['transaction_type'] = 'new'
        else:
            doc_hit['transaction_type'] = 'update'
        doc_hit['href'] = doc_hit['url']
        return doc_hit

    lh = LatestHistories(get_today() - timedelta(10), True).get_page(1)
    return [refine(hit) for hit in lh['hits']]


def index(request):
    context = {
        'messenger': standard_messages,
        'title': standard_messages['This_Domain'],
        'description': standard_messages['og_description'],
        'r_path': f'/eu/search',
        'form': SearchForm.default(),
        'filter_visibility': 'w3-hide',
        'featured_acts': get_featured('eu', FEATURED['eu']),
        'covid_acts': get_covid(),
        'recent_acts': get_recents(),
        'languages_and_domains': LANGUAGE_DOMAIN,
        'url_path': '',
        'url': standard_messages['lexparency_url']
    }
    return render(request, 'land.html', context)


def handle_obsolete_document_path(_, obsolete_document_path):
    """ Guess what! Even more legacy path handling. """
    if obsolete_document_path == 'eu':
        return redirect('/', permanent=False)
    raise HTTPExceptions.GONE(obsolete_document_path)
