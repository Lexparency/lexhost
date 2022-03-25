from django.shortcuts import redirect, render

from lexhost.apps.bot_api.views import diamonds
from lexhost.apps.search import search_corpus, search_document


def corpus_search(request):
    if request.GET:
        if 'search_words' in request.GET:
            if request.GET['search_words'].strip() == '':
                return redirect(request.path, permanent=False)
        else:
            return redirect(request.path, permanent=False)
    return search_corpus(request.path, request.GET)


# @app.route('/<domain>/<document_id>/search')
def document_search(request, domain, document_id):
    id_local = diamonds.get_canonical(document_id)
    all_versions = request.GET.get('all_versions') is not None
    context = {'all_versions': (all_versions * 'checked'),
               'document_id': document_id, 'versions': ''}
    context.update(search_document(request.path, domain, id_local,
                                   words=request.GET.get('search_words', ''),
                                   page=int(request.GET.get('page', 1)),
                                   all_versions=all_versions))
    return render(request, 'search_document.html', context=context)
