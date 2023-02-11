import json
import os
import re
from datetime import datetime, date

from elasticsearch_dsl import Q
from jsonschema import validate
from lxml import etree as et
from lexref import Reflector

from legislative_act.history import DocumentHistory, DocumentVersion
from legislative_act.model import Search, Article
from legislative_act.provider import Preamble
from legislative_act.searcher import BasicSearcher
from legislative_act.toccordior import ContentsTable
from settings import LANG_2, DEFAULT_IRI, BOTAPI
from views.read import strip_title, article_p, Diamonds


amendment_to = {
    "de": re.compile(r"Änderung(en)?\sder\s"),
    "en": re.compile(r"Amendments?\s(of|to)\s"),
    "es": re.compile(r"Modificacion(es)?\s(del|de la)\s"),
}[LANG_2]
li_label = re.compile(r'<li [^>]*?data-title="(?P<label>[^"]+)"[^>]*>')
anchor = re.compile(r"</?a[^>]*>")
diamonds = Diamonds()
SDS = " " + chr(8211) + " "
STATIC_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

with open(os.path.join(STATIC_PATH, "../static/botapi_recents.schema.json")) as f:
    recents_schema = json.load(f)
with open(os.path.join(STATIC_PATH, "../static/botapi_doc.schema.json")) as f:
    doc_schema = json.load(f)


def extract_amends(in_text):
    m = amendment_to.match(in_text)
    if m is None:
        return
    d = Reflector(LANG_2.upper(), "annotate")(in_text)
    try:
        return d[0]["references"][0]["href"]
    except (KeyError, IndexError):
        return


def mark_down(text):
    """Since the correct display of list-item labels depends on the correct
    style-sheet, it's better to place the label as actual text behind the
    li-tag. Also remove anchors, in order to reduce traffic.
    """
    # TODO: Clarify: What about: images, tables, equations
    text = li_label.sub(r"<li>\g<label> ", text)
    text = anchor.sub("", text)
    return text


def document_name(id_human, pop_acronym, id_local):
    if pop_acronym is not None:
        if id_human is not None:
            return pop_acronym + SDS + id_human
        return pop_acronym
    if id_human is not None:
        return id_human
    return id_local


class LatestHistories(BasicSearcher):
    MAX_PAGES = 100

    def __init__(self, date_from, single_step):
        """Provide recent db-changes.
        :param date_from: provide all changes from date_from onwards.
        :param single_step: provide directly all changes.
        """
        if type(date_from) is str:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")
        super().__init__()
        self.date_from = date_from
        self.single_step = single_step

    def search(self):
        return Search().query(
            "nested",
            path="availabilities",
            query=Q(
                "range",
                availabilities__date_document={
                    "gte": self.date_from,
                    "lte": date.today(),
                },
            ),
        )

    def display_hit(self, hit):
        id_local = diamonds.get_alias(hit.meta.id.split("-")[-1])
        result = {
            "id_local": id_local,
            "bot_url": DEFAULT_IRI + f"/{BOTAPI}/{id_local}.json",
        }
        try:
            result["date_document"] = sorted(
                [a["date_document"] for a in hit["availabilities"] if a["available"]]
            )[-1]
        except IndexError:  # TODO: These cases should be displayed somehow!
            return None
        if self.single_step:
            dt = DocumentBot("eu", id_local).get(full=False)
            result.update(dt["head"])
            result["body"] = dt["body"]
        return result

    def enhance_results(self, results, page=1):
        result = super().enhance_results(results, page=page)
        result.pop("total")
        validate(result, recents_schema)
        return result


class DocumentBot:
    def __init__(self, domain, doc_id):
        self.id_local = diamonds.get_canonical(doc_id)
        self.dh = DocumentHistory.get(f"{domain}-{self.id_local}")
        self.dv = DocumentVersion.get(domain, self.id_local, self.dh.latest_available)
        self.dv.toc = ContentsTable.get(self.dv.toc.meta.id)
        self.d_url = DEFAULT_IRI + f"/{domain}/{doc_id}/"
        self.d_name = document_name(
            self.dv.cover.id_human,
            self.dv.cover.pop_acronym,
            self.dv.cover.abstract.id_local,
        )

    def iter_implemented_by(self):
        changes = {
            a.href.strip("/").split("/")[-1]
            for a in self.dv.cover.amends
            if a.href.startswith(DEFAULT_IRI)
        }
        s = (
            Search()
            .filter("term", doc_type="cover")
            .filter("terms", abstract__id_local=list(changes))
            .filter("term", abstract__is_latest=True)
        )
        for hit in s.scan():
            try:
                for a in hit.amended_by:
                    if a.href == self.d_url:
                        try:
                            if a.implemented:
                                yield hit.abstract.id_local
                        except AttributeError:
                            continue
            except AttributeError:
                continue

    @property
    def implemented_by(self):
        ids = set(self.iter_implemented_by())
        return sorted({DEFAULT_IRI + f"/eu/{id_local}/" for id_local in ids})

    @property
    def head(self):
        result = {
            "in_force": self.dv.cover.abstract.in_force,
            "title": self.dv.cover.title,
            "name": self.d_name,
            "url": self.d_url,
        }
        implemented_by = self.implemented_by
        if implemented_by:
            result["implemented_by"] = implemented_by
        if self.dv.cover.pop_title is not None:
            result["pop_title"] = self.dv.cover.pop_title
        if self.dv.cover.pop_acronym is not None:
            result["pop_acronym"] = self.dv.cover.pop_acronym
        return result

    def art2dict(self, art: Article, transaction_type=None):
        d = {
            "url": self.d_url + art.meta.id.split("-")[2] + "/",
            "title": strip_title(art.heading.title),
            "name": article_p.sub("Art.", art.heading.ordinate) + " " + self.d_name,
            "body": mark_down(art.body.dressed),
        }
        if transaction_type is not None:
            d["transaction_type"] = transaction_type
        if d["title"] is not None:
            at = extract_amends(d["title"])
            if at is not None:
                d["amendment_to"] = at
        return d

    def preamble_dict(self):
        return {
            "url": self.d_url + "PRE/",
            "title": self.dv.preamble.ordinate,
            "name": self.dv.preamble.ordinate,
            "body": mark_down(
                et.tostring(
                    Preamble.render_preamble_body(self.dv.preamble),
                    encoding="unicode",
                    method="html",
                )
            ),
        }

    def iter_body_items(self, full):
        s2g = self.dh.sub_to_global_id(self.dh.latest_available)
        if full:
            yield self.preamble_dict()
            for a in self.dv.articles:
                yield self.art2dict(a)
        else:
            for sub_id, change in self.dh.sub_id_change(self.dh.latest_available):
                if change == "delete":
                    yield {
                        "transaction_type": "delete",
                        "url": self.d_url + sub_id + "/",
                    }
                else:
                    yield self.art2dict(Article.get(s2g[sub_id]), change)

    def get_structure(self):
        e = self.dv.toc.toccordior("", method="xml")
        for leaf in e.xpath("//Leaf"):
            leaf.attrib["URL"] = DEFAULT_IRI + leaf.attrib["URL"]
        for container in e.xpath("//Container"):
            container.attrib["URL"] = self.d_url + "#" + container.attrib["URL"]
        return e

    def get(self, full=True):
        result = {
            "head": self.head,
            "structure": et.tostring(  # TODO: only provide structure if it has changed
                self.get_structure(), method="xml", encoding="unicode"
            ),
            "body": list(self.iter_body_items(full)),
        }
        if full:
            # since the not-full variant is only provided via the single_step
            # option. The validation will be done on that end already.
            validate(result, doc_schema)
        return result
