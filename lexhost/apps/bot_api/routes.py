from datetime import date
from django.http import JsonResponse

from .views import LatestHistories, DocumentBot
from ..dbmap import HistoryList


# @botapi.route('/dbmap.json')
def dbmap(request):
    only_availables = request.GET.get('only_availables') not in (None, 'False', '0')
    hl = HistoryList(only_availables)
    return JsonResponse(hl.scan())


# @botapi.route('/recents.json')
def recents(request):
    single_step = request.GET.get('single_step') not in (None, 'False', '0')
    date_from = request.GET.get('date_from', date.today())
    page = int(request.GET.get('page', 1))
    lh = LatestHistories(date_from, single_step)
    return JsonResponse(lh.get_page(page))


# @botapi.route('/<id_local>.json')
def botapi_get_document(_, id_local):
    return JsonResponse(DocumentBot('eu', id_local).get())
