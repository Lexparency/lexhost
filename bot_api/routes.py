from datetime import date

from flask import Blueprint, request, jsonify

from bot_api.views import LatestHistories, DocumentBot
from views.dbmap import HistoryList


def create_botapi(cachier=None):
    botapi = Blueprint("botapi", __name__)

    def dbmap():
        only_availables = request.args.get("only_availables") not in (
            None,
            "False",
            "0",
        )
        hl = HistoryList(only_availables)
        return jsonify(hl.scan())

    if cachier is not None:
        dbmap = cachier(dbmap)
    botapi.route("/dbmap.json")(dbmap)

    @botapi.route("/recents.json")
    def recents():
        single_step = request.args.get("single_step") not in (None, "False", "0")
        date_from = request.args.get("date_from", date.today())
        page = int(request.args.get("page", 1))
        lh = LatestHistories(date_from, single_step)
        return jsonify(lh.get_page(page))

    @botapi.route("/<id_local>.json")
    def botapi_get_document(id_local):
        return jsonify(DocumentBot("eu", id_local).get())

    return botapi
