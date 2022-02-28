from datetime import timedelta

from elasticsearch import NotFoundError
from werkzeug.datastructures import MultiDict

from legislative_act.provider import DocumentProvider
from legislative_act.searcher import CorpusSearcher
from legislative_act.utils.generics import get_today
from bot_api import LatestHistories
from views.read import Diamonds
from views.search import SearchForm


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
    query = SearchForm.parse(MultiDict(dict(search_words='COVID')))
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
