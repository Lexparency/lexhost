from math import ceil
import datetime
from dataclasses import dataclass
from elasticsearch_dsl import query
from abc import ABCMeta, abstractmethod
from functools import partial

from . import model as dm
from .utils import paginator


def specify_for_humans(cover: dm.Cover, format_=1):
    """
    TODO: Unittest!
    The format of the return value depends on the choice of version
    :return title: String with human readable title/identifier for the document.
    """
    id_human = cover.id_human or cover.abstract.id_local
    if format_ == 1:
        return id_human
    title = cover.pop_title
    if title is None:
        return id_human
    else:
        pop_acronym = cover.pop_acronym
        if pop_acronym is not None:
            title = "{} ({})".format(title, pop_acronym)
    if format_ == 2:
        return title
    else:  # format 3
        if title is None:
            return id_human
        return id_human + " {} ".format(chr(8212)) + title


@dataclass
class Filter:
    # TODO: Consider and include the possibility to host several legal domains.
    #  This would require further filters!
    # TODO: Consider using WTForms instead of dataclass.
    in_force: bool or None = None
    date_from: datetime.date or None = None
    # Default such that all documents are covered:
    date_to: datetime.date or None = None
    # Perform full-body search if True,
    # otherwise search only within cover titles:
    deep: bool = False
    serial_number: int or None = None
    type_document: tuple = ()


def display_dictionary(hit, document_focus=False):
    # TODO: Unittest this function
    cover = dm.Cover.get(
        "{}-{}-COV-initial".format(hit.abstract.domain, hit.abstract.id_local)
    )
    if hit.doc_type == "cover":
        id_human = specify_for_humans(cover, format_=3)
        href = f"/{hit.abstract.domain}/{hit.abstract.id_local}/"
    else:
        href = "/{}/".format("/".join(hit.meta.id.split("-")[:-1]))
        if hit.doc_type == "article":
            id_human = hit.heading.ordinate
        else:
            assert hit.doc_type == "preamble"
            id_human = hit.ordinate
        if not document_focus:
            id_human = "{}, {}".format(id_human, specify_for_humans(cover, format_=2))
    if hit.doc_type != "cover":
        try:
            highlights = "... {} ...".format(
                " ... ".join(getattr(hit.meta.highlight, "body.stripped"))
            )
        except AttributeError:  # i.e. no matches in the body
            highlights = None
    else:
        highlights = None
    try:
        title = getattr(hit.meta.highlight, "heading.title")[0]
    except AttributeError:
        if hit.doc_type == "article":
            try:
                title = hit.heading.title
            except AttributeError:
                title = hit.heading.ordinate
        else:
            title = hit.title
    return {
        "id_human": id_human,
        "title": title,
        "highlights": highlights,
        "href": href,
    }


class BasicSearcher(metaclass=ABCMeta):
    PAGE_SIZE = 20
    MAX_PAGES = 15

    def __init__(self):
        self.page = 1

    @abstractmethod
    def search(self):
        pass

    @abstractmethod
    def display_hit(self, hit) -> dict:
        pass

    def enhance_results(self, results, page=1):
        return {
            "total": results.hits.total.value,
            "total_pages": ceil(results.hits.total.value / self.PAGE_SIZE),
            # TODO: Take into account the possibility that only a lower bound
            #  provided: https://www.elastic.co/guide/en/elasticsearch/
            #  reference/7.0/breaking-changes-7.0.html#hits-total-now-object-search-response
            "current_page": page,
            "hits": [h for h in map(self.display_hit, results) if h is not None],
        }

    def get_page(self, page: int):
        self.page = page
        page = min(self.MAX_PAGES, page)
        s = self.search()
        from_ = (page - 1) * self.PAGE_SIZE
        s = s[from_ : from_ + self.PAGE_SIZE]
        r = s.execute()
        return self.enhance_results(r, page=page)


class WordsSearcher(BasicSearcher, metaclass=ABCMeta):

    fragment_size = 150
    number_of_fragments = 3

    date_score_function = query.SF(
        "exp", abstract__date_publication={"scale": "365d", "decay": 0.5}
    )

    score_score_function = query.SF(
        "exp", score_multiplier={"origin": -1000, "scale": 50, "offset": 1000}
    )

    multi_match = partial(
        query.MultiMatch,
        fields=[
            "body.stripped",
            "heading.title^3",
            "title^3",
            "pop_acronym^4",
            "pop_title^10",
        ],
    )

    @abstractmethod
    def search(self):
        s = (
            dm.Search()
            .highlight(
                "body.stripped",
                fragment_size=self.fragment_size,
                number_of_fragments=self.number_of_fragments,
                fragmenter="simple",
                pre_tags=["<mark>"],
                post_tags=["</mark>"],
            )
            .highlight(
                "heading.title",
                number_of_fragments=0,
                fragmenter="simple",
                pre_tags=["<mark>"],
                post_tags=["</mark>"],
            )
        )
        return s.query("bool", must=[self.multi_match(query=self.words)])

    def __init__(self, words: str):
        super().__init__()
        self.words = words

    def enhance_results(self, results, page=1):
        result = super().enhance_results(results, page=page)
        result["pages"] = paginator(self.MAX_PAGES, result["total_pages"], page)
        return result


class CorpusSearcher(WordsSearcher):
    def __init__(self, words, f: Filter):
        super().__init__(words)
        self.filter = f

    def search(self):
        s = super().search()
        # To make sure that result page is not filled with several versions
        # of the same article:
        s = s.filter("term", abstract__is_latest=True)
        # Setting the filters:
        if self.filter.in_force is not None:
            s = s.filter("term", abstract__in_force=self.filter.in_force)
        if (self.filter.date_from or self.filter.date_to) is not None:
            date_from = self.filter.date_from or datetime.date(1900, 1, 1)
            date_to = self.filter.date_to or datetime.date.today()
            s = s.filter(
                "range", abstract__date_publication={"gte": date_from, "lte": date_to}
            )
        if not self.filter.deep:
            s = s.filter("term", doc_type="cover").filter(
                "term", abstract__is_latest=True
            )
        else:  # currently no searching within preamble:
            s = s.filter("terms", doc_type=["cover", "article"])
        if len(self.filter.type_document) > 0:
            s = s.filter(
                "terms", abstract__type_document=list(self.filter.type_document)
            )
        if self.filter.serial_number is not None:
            s = s.filter("term", abstract__serial_number=self.filter.serial_number)
        s.query = query.FunctionScore(
            query=s.query, functions=[self.date_score_function]
        )
        return s

    def display_hit(self, hit):
        return display_dictionary(hit)


class DocumentSearcher(WordsSearcher):
    def __init__(self, words, domain, id_local, all_versions=False):
        super().__init__(words)
        self.domain = domain
        self.id_local = id_local
        self.all_versions = all_versions

    def search(self):
        s = super().search()
        if not self.all_versions:
            s = s.filter("term", abstract__is_latest=True)
        s = s.filter("term", doc_type="article")
        s = s.filter("term", abstract__id_local=self.id_local)
        s = s.filter("term", abstract__domain=self.domain)
        return s

    def display_hit(self, hit):
        return display_dictionary(hit, document_focus=True)
