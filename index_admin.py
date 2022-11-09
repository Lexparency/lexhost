from datetime import datetime
from time import sleep
import logging

from elasticsearch.exceptions import ConnectionTimeout
from flask import Blueprint, make_response, request
from werkzeug.exceptions import NotFound

from legislative_act.receiver import DocumentReceiver
from utils import check_trustworthy, get_document_history
from views.nationals import write_nationals
from views.read import Read

logger = logging.getLogger(__name__)


def create_index_admin():
    index_admin = Blueprint("index_admin", __name__)

    @index_admin.route("/<domain>/", methods=["POST"])
    @check_trustworthy
    def receive(domain):
        # TODO: check if exists. If so, return error.
        dr = DocumentReceiver.relaxed_instantiation(request.data.decode("utf-8"))
        if domain != dr.domain:
            return make_response("Inconsistent document domain", 422)
        try:
            dr.save()
        except Exception as e:
            logger.error(f"Failed to load /{domain}/{dr.id_local}/{dr.version}")
            dh = get_document_history(domain, dr.id_local)
            if dh.latest == dr.version:
                dh.remove_latest()
            if type(e) is ConnectionTimeout:
                sleep(10)  # give elasticsearch some time
                dr.save()
            else:
                raise
        return make_response(f"Uploaded to /{domain}/{dr.id_local}/{dr.version}", 200)

    @index_admin.route("/<domain>/<id_local>/", methods=["DELETE"])
    @check_trustworthy
    def purge(domain, id_local):
        try:
            dh = get_document_history(domain, id_local)
            dh.purge()
        except NotFound:
            return make_response("Seems like someone deleted it already", 200)
        return make_response(f"\nAll versions of /{domain}/{id_local}/ deleted", 200)

    @index_admin.route("/<domain>/<id_local>/<version>", methods=["DELETE"])
    @check_trustworthy
    def remove_latest(domain, id_local, version):
        dh = get_document_history(domain, id_local)
        if dh.latest != version:
            raise NotImplemented("Can only delete if given version is latest.")
        dh.remove_latest()
        return make_response(f"Deleted /{domain}/{id_local}/{version}")

    @index_admin.route("/_national_ref/<domain>/<id_local>/<sub_id>/", methods=["POST"])
    @index_admin.route("/_national_ref/<domain>/<id_local>/", methods=["POST"])
    @index_admin.route("/_national_ref/<domain>/", methods=["POST"])
    @check_trustworthy
    def write_national_reference(domain, id_local=None, sub_id="TOC"):
        d = request.json
        target = domain
        if id_local is not None:
            target = f"{target}-{id_local}"
        if sub_id not in ("TOC", "COV"):
            target = f"{target}-{sub_id}"
        c = 0
        for c, kwargs in enumerate(d["data"]):
            if "target" in kwargs:
                assert kwargs["target"].startswith(target)
            else:
                kwargs["target"] = target
            write_nationals(**kwargs)
        return make_response(f"Posted {c+1} references.")

    @index_admin.route("/_unavailable/<domain>/<id_local>/<version>", methods=["POST"])
    @check_trustworthy
    def insert_unavailable(domain, id_local, version):
        """Incorporates information that a certain version exists, but cannot be
        provided in the necessary format.
        """

        def parse_date(in_string):
            return datetime.strptime(in_string, "%Y-%m-%d").date()

        dh = get_document_history(domain, id_local)
        d = request.json
        dh.insert_unavailable(version, parse_date(d["date_document"]), d.get("after"))
        return make_response(f"Accepted /{domain}/{id_local}/{version}")

    @index_admin.route("/_metadata/<domain>/<id_local>/", methods=["PUT"])
    @check_trustworthy
    def update_metadata(domain, id_local):
        dh = get_document_history(domain, id_local)
        for key, value in request.args.items():
            if key == "in_force":
                if value not in ("True", "False", "None"):
                    raise ValueError(f"{value} not a valid in-force value.")
                dh.in_force = eval(value)
            else:
                raise NotImplemented(f"Attribute {key} cannot yet be changed.")
        Read.clear_all_caches()
        return make_response(f"\nUpdated /{domain}/{id_local}/", 200)

    return index_admin
