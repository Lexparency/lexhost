from flask import render_template
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import NotFound

from legislative_act.provider import DocumentProvider
from legislative_act.searcher import CorpusSearcher
from views.exceptions import handle_as_404
from .shortcuts import ShortCutter
from .form import SearchForm
from views.standard_messages import standard_messages


@handle_as_404
def search_document(path, domain, id_local, words, page, all_versions=False):
    document = DocumentProvider(domain, id_local)
    latest_version = document.latest_available
    if latest_version is None:
        raise NotFound(f'/{domain}/{id_local}/ is not available.')
    cover = document.get_cover(latest_version).flat_dict()
    result = document.search(words, page=page, all_versions=all_versions)
    if page == 1:
        for hit in ShortCutter.hits_from(
                words, document_context=f'/{domain}/{id_local}'):
            result['hits'].insert(0, hit)
    result['pages'] = SearchForm(search_words=words)\
        .repaginator(result['pages'], path)
    content = {
        'search_words': words,
        'messenger': standard_messages,
        'cover': cover,
        'document_title': cover.get('pop_title') or cover.get('title'),
        'title': "{} \"{}\"".format(
            standard_messages["search_results_for"], words),
        'description': str(result['total']) + ' ' + standard_messages['result_s'][1],
        'hits': result,
        'r_path': path
    }
    return content


def search_corpus(path: str, args: MultiDict):
    # TODO: include filter on domain
    query = SearchForm.parse(args)
    if query is not None:
        form = SearchForm(**query).form_config()
        page = int(args.get('page', 1))
        searcher = CorpusSearcher(query['search_words'], query.as_filter())
        result = searcher.get_page(page)
        if page == 1:
            hrefs = {hit['href'] for hit in result['hits']}
            for hit in ShortCutter.hits_from(query['search_words']):
                if hit['href'] not in hrefs:  # avoiding double appearance.
                    result['hits'].insert(0, hit)
        result['pages'] = query.repaginator(result['pages'], path)
        try:
            title = "{} \"{}\"".format(standard_messages["search_results_for"],
                                       query['search_words'])
        except KeyError:
            title = standard_messages["search_results"]
        description = str(result['total']) + ' ' + standard_messages['result_s'][1]
    else:
        title = standard_messages["advanced_search"]
        result = None
        form = SearchForm.default()
        description = standard_messages['advanced_search']
    content = {
        'messenger': standard_messages,
        'title': title,
        'description': description,
        'hits': result,
        'query': query,
        'r_path': path,
        'form': form,
        'filter_visibility': ''
    }
    return render_template('search_corpus.html', **content)
