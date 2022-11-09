"""
Data model for legislative acts.
This model involves various classes representing various aspects / components
of a legislative abstract. Since with the release of elasticsearch 6, the
definition of different doc_types is not fully supported, this model includes
an extra field for each class indicating the doc_type, which is then assigned
when the method save() is called. Currently this solution relies on the name of
the class. Therefore note the following
!! BIG FAT WARNING !!:
    When subclassing the Document-Classes defined here, name it identical. E.g.:
    class Cover(document.Cover):
        ...
"""
from __future__ import annotations
from collections import defaultdict
from functools import partial, lru_cache
from itertools import product
import datetime

from elasticsearch import ConnectionTimeout
from elasticsearch_dsl import (
    Document,
    Date,
    Boolean,
    Integer,
    Nested,
    analyzer,
    InnerDoc,
    Keyword,
    Text,
    Index,
    connections,
    MetaField,
    Object,
    Search,
    AttrList,
)
from elasticsearch_dsl.utils import ObjectBase
from elasticsearch_dsl.document import IndexMeta

from legislative_act.utils.generics import get_today, retry
from .es_settings import numbers, create_analysis
from settings import LANG_2, DEFAULT_IRI

connections.create_connection(hosts=["localhost"])

language = LANG_2
index_name = f"legex-{language}"

index = Index(index_name)

index.settings(**numbers)

zimple = analyzer("zimple", tokenizer="lowercase")

language_analyzer = create_analysis(language)

Search = partial(Search, index=index_name)

analyzed_text = partial(
    Text,
    analyzer=language_analyzer,
    # to be used by the highlighter/fragmenter:
    store=True,
    term_vector="with_positions_offsets",
)


class AutoInspector(ObjectBase):
    @classmethod
    def get_fields(cls):
        return cls._doc_type.mapping.to_dict()["properties"].keys()


def art_sub_id(sub_id):
    """Checks whether the sub_id <sub_id> could come from an article."""
    return sub_id not in ("COV", "TOC", "PRE") and not sub_id.startswith("DEF_")


# noinspection PyRedeclaration
class Document(Document):
    def as_dump(self):
        return {
            "_index": index_name,
            "_type": self.meta.doc_type,
            "_id": self.meta.id,
            "_source": self.to_dict(),
        }

    @classmethod
    @retry(ConnectionTimeout, 3, 10)
    def get(cls, *args, **kwargs) -> VersionsMap:
        """Just a pass-through for the retry on ConnectionTimeout"""
        return super().get(*args, **kwargs)


class Anchor(InnerDoc):
    """For neatly displayed anchors on the sidebar.
    Currently, related documents (e.g. (cites, cited_by, based_on, ...)
    are displayed rather minimalistic, showing only the celex-id or some
    self-constructed spoken ID. If such information is provided as
    Anchor-instance, it can be displayed in html as follows:
    <a href={url} title={title}>{text}</a>
    """

    changers = ("amended_by", "corrected_by")
    text = Keyword(required=True)
    href = Keyword(required=True)
    title = Keyword()
    implemented = Boolean()  # only relevant for changer

    def __hash__(self):
        return hash(self.href)


class Abstract(InnerDoc, AutoInspector):
    """
    This class represents and holds the most fundamental metadata
    of a legal expression.
    It is needed for search filter and to be displayed on the interface.
    """

    # (eli:based_on? lxp:...) Document domain, e.g. eu, de, de-nrw:
    domain = Keyword(required=True)
    # (eli:id_local? lxp:...) ID of the encompassing document. Previously celex
    id_local = Keyword(required=True)
    # (lxp:...) Indication for which versions, this is a valid resource.
    version = Keyword(multi=True)
    # (eli:type_document) Regulation/Directive/Decision/...  (lex_type)
    type_document = Keyword()
    # (lxp:...) 575 in Regulation (EU) 575/2013 (no ELI correspondence)
    serial_number = Integer()
    in_force = Boolean()  # (eli:in_force) Currently in force?
    # for its use within Article instances, this is equivalent to "is_latest"
    # Since the version-constellation anomaly for the CRR, this field is not
    # any more always correct :(
    date_publication = Date()  # (eli:date_publication) date of publication
    # is true if "version" is latest version available.
    # The purpose of this flag is for filtering on a full-body search, to avoid
    # that several versions of the same article are provided.
    # BUT!: If an Article has become obsolete by a newer version. The is_latest
    # flag shall be False.
    is_latest = Boolean(required=True)

    def __eq__(self, other):
        """For the incorporation of new document versions it is important
        that two corresponding articles are recognized as being different,
        not just because their abstract's version attribute differs.
        """
        if type(other) is not type(self):
            return False
        for name in ("domain", "id_local", "type_document", "serial_number"):
            if getattr(self, name) != getattr(other, name):
                return False
        return True


class Twix(InnerDoc):
    """
    Since the multi-field feature of elasticsearch has a size limit,
    text fields that are meant to be used for search and for displaying,
    are stored in two sub-fields:
        - "stripped" for raw plain text versions of the field.
            For searching and highlighting.
        - "dressed" for the versions including markup.
            For displaying on the article view etc..
    """

    stripped = analyzed_text()
    dressed = Text(index=False, store=True)

    def __eq__(self, other):
        """For now, we consider two Twixes to be equal
        if their stripped versions are equal."""
        if type(other) is not Twix:
            return False
        return self.stripped == other.stripped


class Base(Document):
    doc_type = Keyword(required=True)
    abstract = Object(Abstract)
    score_multiplier = Integer()  # For better controlled search-ranking

    @classmethod
    def get_doc_type(cls):
        return cls.__name__.lower()

    def __init__(self, **kwargs):
        kwargs["doc_type"] = self.get_doc_type()
        super().__init__(**kwargs)

    @property
    def version(self):
        return self.abstract.version[0]

    @property
    def sub_id(self):
        """The ID convention is as follows:
        <domain>-<id_local>-<sub_id>-<version>
        """
        return self.meta.id.split("-")[-2]

    class Meta:
        dynamic = MetaField("strict")

    @classmethod
    def _matches(cls, hit):
        # Base and all derived classes are abstract classes,
        # make sure they never get used for deserialization
        return False

    def flat_dict(self) -> dict:
        """
        Provide a dictionary without all the Twix and Nested fuzz.
        """

        def flatten(d: dict):
            for name, value in list(d.items()):
                if type(value) is dict:
                    if set(value.keys()) == {"stripped", "dressed"}:
                        d[name] = value["dressed"]
                    elif name == "heading":
                        for key in list(value.keys()):
                            if key in d:
                                break
                            d[key] = value.pop(key)
                        else:  # no break occurred
                            del d["heading"]
                    else:
                        flatten(value)
                elif type(value) is list:
                    for item in value:
                        if type(item) is dict:
                            flatten(item)

        result = self.to_dict()
        flatten(result)
        abstract = result.pop("abstract")
        result.update(abstract)
        return result


class VersionAvailability(InnerDoc):
    version = Keyword(required=True)  # or "version_label"
    date_document = Date(required=True)  # eli:date_document
    available = Boolean(required=True)
    date_received = Date(required=True)

    def __init__(self, **kwargs):
        if "date_received" not in kwargs:
            kwargs["date_received"] = get_today()
        super().__init__(**kwargs)


class ExposedAndHiddenVersions(InnerDoc):
    """exposed_versions should always include hidden_version
    as first item -- cf. usage in VersionsMap.as_mapping."""

    sub_id = Keyword(required=True)
    hidden_version = Keyword(required=True)
    # versions list for which hidden_version serves as resource.
    # Contains value of "hidden_version" as first item.
    exposed_versions = Keyword(required=True, multi=True)


def uniquify_list(inp):
    a_sort = partial(sorted, key=lambda x: x.href)
    u_list = a_sort({a.href: a for a in inp}.values())
    # just a_sort(inp) == u_list did'nt work :/
    if [a.href for a in a_sort(inp)] == [a.href for a in u_list]:
        return False
    for _ in range(len(inp)):
        inp.pop()
    for a in u_list:
        inp.append(a)
    return True


@index.document
class VersionsMap(Document):
    availabilities = Nested(VersionAvailability)
    exposed_and_hidden = Nested(ExposedAndHiddenVersions)
    doc_type = Keyword(required=True)

    def datify(self):
        for va in self.availabilities:
            for dt in ("document", "received"):
                try:
                    value = getattr(va, f"date_{dt}").date()
                except AttributeError:
                    pass
                else:
                    setattr(va, f"date_{dt}", value)
        return self  # nice for chaining

    @classmethod
    def from_es(cls, *args, **kwargs):
        result = super().from_es(*args, **kwargs)
        result.datify()
        return result

    @classmethod
    def get(cls, *args, **kwargs) -> VersionsMap:
        """No idea, when ES converts to datetime and when not."""
        result = super().get(*args, **kwargs)
        result.datify()
        return result

    def __init__(self, **kwargs):
        kwargs["doc_type"] = "versionsmap"
        super().__init__(**kwargs)

    def __hash__(self):
        return id(self)

    @property
    def exposed_to_hidden(self) -> dict:
        return {
            (eh.sub_id, exposed_version): eh.hidden_version
            for eh in self.exposed_and_hidden
            for exposed_version in eh.exposed_versions
        }

    @property
    @lru_cache()
    def hidden_to_exposed(self) -> dict:
        result = defaultdict(dict)
        for eh in self.exposed_and_hidden:
            result[eh.sub_id][eh.hidden_version] = eh.exposed_versions
        return result

    @property
    def version_to_availability(self):
        return {a.version: a.available for a in self.availabilities}

    @property
    def version_to_date(self) -> dict:
        return {a.version: a.date_document for a in self.availabilities}


@index.document
class Cover(Base, AutoInspector):
    """
    Exemplary values for id: 32013R0575, TEU, TFEU, CETA
    """

    source_iri = Keyword(required=True)  # Document landing page of the source provider
    source_url = Keyword(  # Eurlex-URL from where the present document
        required=True, index=False  # has been downloaded
    )
    # (lxp:...) title without amendment- and repealing- information
    title_essence = analyzed_text()
    # (lxp:...) E.g. "Capital Requirements Regulation" for Regulation EU 57/2013
    pop_title = Text(analyzer=language_analyzer)
    # (lxp:...) E.g. "CRR" for Regulation EU 575/2013
    pop_acronym = Text(analyzer=zimple)
    # (lxp:...) ID of document in self.language, e.g. Regulation (EU) No 57/2013
    id_human = Keyword(index=False)
    # Fields from the ELI metadata:
    # (eli:title) Full title, e.g. "Commission Regulation (EU) 112/2008 from ..."
    title = analyzed_text()
    first_date_entry_in_force = Date()  # (eli:first_date_entry_in_force)
    date_no_longer_in_force = Date()  # (eli:date_no_longer_in_force)
    date_applicability = Date()  # (eli:date_applicability)
    # (eli:passed_by) e.g. "European Parliament":
    passed_by = Keyword(multi=True)
    based_on = Nested(Anchor)  # -> (eli:based_on)
    is_about = Text(analyzer=language_analyzer, multi=True)  # (eli:is_about)
    # -> (eli:amends) List of Document IDs to be repealed:
    repealed_by = Nested(Anchor)
    corrected_by = Nested(Anchor)
    amended_by = Nested(Anchor)
    completed_by = Nested(Anchor)
    repeals = Nested(Anchor)
    corrects = Nested(Anchor)
    amends = Nested(Anchor)
    completes = Nested(Anchor)
    cites = Nested(Anchor)  # -> (eli:cites)
    cited_by = Nested(Anchor)  # -> (eli:cited_by)

    @classmethod
    def iter_anchors(cls):
        for field in cls.get_fields():
            attribute = cls._doc_type.mapping.properties[field]
            if type(attribute) is not Nested:
                continue
            # noinspection PyProtectedMember
            if attribute._doc_class is Anchor:
                yield field

    @classmethod
    @lru_cache()
    def forth_back_anchors(cls):
        """Dynamically builds back and forth mapping of related anchor-attributes:
        I.e. {'amdends': 'amended_by', 'amended_by': 'amdends', 'cites': ...}
        """

        def is_pair(f, b):
            if not f.endswith("s"):
                return False
            if b.startswith(f[:-1]) and b.endswith("d_by"):
                return True
            return False

        anchors = list(cls.iter_anchors())
        result = {
            forth: back
            for forth, back in product(anchors, anchors)
            if forth > back and is_pair(forth, back)
        }
        result.update({back: forth for forth, back in list(result.items())})
        return result

    def consist_relations(self):
        # TODO: set "implemented" to "False" if relation in Anchors.changers
        cls = type(self)
        fba = cls.forth_back_anchors()
        ia = self.as_anchor()
        for ref_name in fba.keys():
            anchors = getattr(self, ref_name)
            for anchor in anchors:
                if not anchor.href.startswith(f"{DEFAULT_IRI}/"):
                    continue
                rel_ref = anchor.href.replace(DEFAULT_IRI, "").strip("/")
                if "/" not in rel_ref:
                    continue
                domain, id_local, *_ = rel_ref.split("/")
                if domain != self.abstract.domain:
                    continue
                for hit in (
                    Search()
                    .filter("term", doc_type="cover")
                    .filter("term", abstract__is_latest=True)
                    .filter("term", abstract__id_local=id_local)
                    .filter("term", abstract__domain=domain)
                    .scan()
                ):
                    backs = set(a.href for a in getattr(hit, fba[ref_name], []))
                    if ia.href not in backs:
                        c = cls.get(hit.meta.id)
                        getattr(c, fba[ref_name]).append(ia)
                        c.save()

    def as_anchor(self) -> Anchor:
        return Anchor(
            href=f"{DEFAULT_IRI}/{self.abstract.domain}/{self.abstract.id_local}/",
            text=self.pop_acronym or self.id_human or self.abstract.id_local,
            title=self.pop_title or self.title_essence or self.title,
        )

    @classmethod
    def date_fields(cls):
        return [
            name
            for name in cls.get_fields()
            if type(cls._doc_type.mapping.properties[name]) is Date
        ] + ["date_publication"]

    def uniquify_referrals(self):
        """Still trouble with: 32004R0726-EN: reference to 32009R0470"""
        changed = False
        for referral in self.iter_anchors():
            changed = changed or uniquify_list(getattr(self, referral, []))
        return changed

    def save(self, **kwargs):
        assert getattr(self, "language", None) in (None, language.upper())
        self.uniquify_referrals()
        return super().save(**kwargs)

    def __eq__(self, other) -> bool:
        if type(self) != type(other):
            return False
        cover_fields = self.get_fields()
        for name in cover_fields:
            left = getattr(self, name)
            right = getattr(other, name)
            if {type(left), type(right)} == {datetime.date, datetime.datetime}:
                mapped = {type(left): left, type(right): right}
                if mapped[datetime.datetime].time() != datetime.time(0, 0):
                    return False
                if mapped[datetime.datetime].date() != mapped[datetime.date]:
                    return False
            elif type(left) is AttrList:
                if set(left) != set(right):
                    return False
            elif left != right:
                return False
        return True

    def flat_dict(self, crumble=False):
        result = super().flat_dict()
        if not crumble:
            return result
        result["referrers"] = []
        for name in self.iter_anchors():
            if name not in result:
                continue
            result["referrers"].append(
                {
                    "name": name,
                    "changer": name in Anchor.changers,
                    "anchors": result.pop(name),
                }
            )
        return result


class Heading(InnerDoc):
    ordinate = analyzed_text()
    title = analyzed_text()


@index.document
class Article(Base):  # A.k.a Article
    heading = Object(Heading)
    body = Object(Twix)

    def __eq__(self, other):
        return self.heading == other.heading and self.body == other.body


class Recital(InnerDoc):
    # Field may also be used by other document types that have no real title
    inferred_title = Keyword()
    body = Object(Twix)


@index.document
class Preamble(Base):
    ordinate = analyzed_text()
    # Actually the remainder that remains after removing all recitals.
    body = Object(Twix)
    recitals = Nested(Recital)


@index.document
class Definition(Base):
    terms = analyzed_text(multi=True)  # Alternative terminology
    body = Object(Twix)


class ContentsTableNode(InnerDoc):
    # Path part of URL + hash-part:
    locator = Keyword(required=True)
    heading = Object(Heading)
    # For constructing the toccordion it's simpler
    # to have the children available:
    children = Keyword(multi=True)


@index.document
class ContentsTable(Base):
    table = Nested(ContentsTableNode)


@index.document
class NationalReference(Document):
    """National legislations that refer to present content"""

    doc_type = Keyword(required=True)
    country_name = Keyword(required=True)  # e.g. Deutschland
    text = Keyword(required=True)  # e.g. §1 BGB
    title = analyzed_text()
    transposes = Keyword(multi=True)  # e.g. ['eu-32013L0036']
    urls = Keyword(required=True, multi=True)
    references = Keyword(required=True, multi=True)
    # e.g. ['eu-32013R0575-ART_92', 'eu-32013R0575', 'eu-32016R0679']

    @classmethod
    def get_doc_type(cls):
        # TODO: Merge with class "base"
        return cls.__name__.lower()

    def __init__(self, **kwargs):
        kwargs["doc_type"] = self.get_doc_type()
        super().__init__(**kwargs)


@index.document
class GenericContentDocument(Document):
    pass


def delete(id_):
    GenericContentDocument.get(id=id_).delete()


content_document_types = [
    cls.__name__.lower()
    for cls in [eval(cl) for cl in dir() if type(eval(cl)) is IndexMeta]
    if issubclass(cls, Base) and cls is not Base
]
