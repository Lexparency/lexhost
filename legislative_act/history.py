from dataclasses import dataclass, field
from functools import wraps
from typing import List
from elasticsearch.exceptions import NotFoundError, ConnectionTimeout
from datetime import date

from . import model as dm
from .model import art_sub_id
from .utils.generics import retry


class VersionNotAvailable(Exception):
    pass


class InconsistentVersionHistory(Exception):
    pass


def flushed(f):
    """Decorator to flush the index before and after execution."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        dm.index.refresh()
        result = f(*args, **kwargs)
        dm.index.refresh()
        return result

    return wrapped


@dataclass
class DocumentVersion:
    """Holds all those ES-Documents
    that in combination represent a document version"""

    version: str
    date_document: date
    cover: dm.Cover
    toc: dm.ContentsTable = None
    preamble: dm.Preamble = None
    articles: List[dm.Article] = field(default_factory=list)
    definitions: List[dm.Definition] = field(default_factory=list)
    available: bool = True

    @property
    def domain(self):
        return self.cover.abstract.domain

    @property
    def id_local(self):
        return self.cover.abstract.id_local

    def iter_parts(self):
        for name in ["cover", "preamble", "toc"]:
            attribute = getattr(self, name)
            if attribute is not None:
                yield attribute
        for part in self.articles:
            yield part
        for part in self.definitions:
            yield part

    def to_dict(self) -> dict:
        return {es_doc.meta.id: es_doc.to_dict() for es_doc in self.iter_parts()}

    def get_history(self):
        try:
            return DocumentHistory.get(f"{self.domain}-{self.id_local}")
        except NotFoundError:
            dh = self.default_version_map()
            dh.save()
            return dh

    @flushed
    def save(self):
        if self.date_document is None:
            raise ValueError("eli:date_document needs to be provided")
        self.get_history().incorporate(self)

    def delete(self):
        """Note that this only deletes those es-documents with the actual
        content. The dm.VersionsMap instance is untouched.
        """
        for es_doc in self.iter_parts():
            es_doc.delete()

    def default_version_map(self) -> dm.VersionsMap:
        result = DocumentHistory(availabilities=[], exposed_and_hidden=[])
        result.meta.id = "{}-{}".format(self.domain, self.id_local)
        return result

    @classmethod
    def get(cls, domain, id_local, version):
        """Creates instance from elasticsearch.
        If no version is provided, the latest version
        (not the latest available version!) is returned.
        """
        vm = DocumentHistory.get("{}-{}".format(domain, id_local))
        if not vm.version_to_availability[version]:
            raise VersionNotAvailable(
                f"For the document with id_local={repr(id_local)} (domain={domain}), "
                f"the version {repr(version)}. is not indexes."
            )
        stg = vm.sub_to_global_id(version)
        return cls(
            version=version,
            date_document=vm.version_to_date[version],
            cover=dm.Cover.get(stg["COV"]),
            toc=dm.ContentsTable.get(stg["TOC"]),
            preamble=dm.Preamble.get(stg["PRE"]),
            articles=[
                dm.Article.get(global_id)
                for sub_id, global_id in stg.items()
                if art_sub_id(sub_id)
            ],
            definitions=[
                dm.Definition.get(global_id)
                for sub_id, global_id in stg.items()
                if sub_id.startswith("DEF_")
            ],
        )


class DocumentHistory(dm.VersionsMap):
    @property
    def id_local(self):
        return self.meta.id.split("-")[1]

    @property
    def domain(self):
        return self.meta.id.split("-")[0]

    @property
    def latest(self):
        for availability in reversed(self.availabilities):
            if availability.date_document <= date.today():
                return availability.version

    @property
    def latest_available(self):
        for availability in reversed(self.availabilities):
            if availability.available and availability.date_document <= date.today():
                return availability.version
        for availability in reversed(self.availabilities):
            # if only the future version is available, then go with that one.
            if availability.available:
                return availability.version

    def sub_to_global_id(self, version):
        result = {
            item.sub_id: "-".join((self.meta.id, item.sub_id, item.hidden_version))
            for item in self.exposed_and_hidden
            if version in item.exposed_versions
        }
        return result

    def get_latest_loaded(self):
        latest_available = self.latest_available
        if latest_available is None:
            return {}
        return {
            part.sub_id: part
            for part in DocumentVersion.get(
                self.domain, self.id_local, latest_available
            ).iter_parts()
        }

    def append_availability(self, availability: dm.VersionAvailability):
        if self.availabilities:
            if availability.version in {a.version for a in self.availabilities}:
                raise InconsistentVersionHistory(
                    f"Version {availability.version} already available "
                    f"for {self.domain}-{self.id_local}."
                )
        self.availabilities.append(availability)

    def incorporate(self, doc: DocumentVersion):
        """Goes through every Article and further ES-documents:
        1) compares each of them with the corresponding latest indexed
            a) if equivalent indexed ES-document is found:
                update version map!
            b) else: save it and update the version map.
        2) save the version map.
        """
        assert doc.domain == self.domain and doc.id_local == self.id_local
        latest_loaded = self.get_latest_loaded()
        latest = self.latest
        self.append_availability(
            dm.VersionAvailability(
                version=doc.version,
                date_document=doc.date_document,
                available=doc.available,
            )
        )
        for new_part in doc.iter_parts():
            if new_part.sub_id == "COV":
                new_part.consist_relations()
            if (
                new_part.sub_id != "COV"
                or latest == self.latest_available
                or latest is None
            ):
                latest_loaded_part = latest_loaded.get(new_part.sub_id)
            else:
                latest_loaded_part = dm.Cover.get(self.sub_to_global_id(latest)["COV"])
            new_part.abstract.is_latest = True
            if latest_loaded_part is None:
                # Case: the new doc has a completely new part.
                new_part.save()
                self.exposed_and_hidden.append(
                    dm.ExposedAndHiddenVersions(
                        sub_id=new_part.sub_id,
                        hidden_version=doc.version,
                        exposed_versions=[doc.version],
                    )
                )
            elif new_part == latest_loaded_part:
                # Case: this part of this version is identical to
                # the corresponding part of the already loaded one.
                self.hidden_to_exposed[new_part.sub_id][
                    latest_loaded_part.version
                ].append(doc.version)
                latest_loaded_part.abstract.version.append(doc.version)
                latest_loaded_part.save()
            else:
                # Case: this part of this version of the document differs
                # from the corresponding part of the already stored version.
                if new_part.sub_id != "COV":
                    latest_loaded_part.abstract.in_force = False
                latest_loaded_part.abstract.is_latest = False
                latest_loaded_part.save()
                try:
                    new_part.save()
                except Exception as e:
                    self.remove_latest()  # basically a rollback
                    raise e
                self.exposed_and_hidden.append(
                    dm.ExposedAndHiddenVersions(
                        sub_id=new_part.sub_id,
                        hidden_version=new_part.version,
                        exposed_versions=[new_part.version],
                    )
                )
        # Finally, set in_force flag of obsolete leaves to False
        availables = [
            a.version
            for a in self.availabilities
            if a.available and a.version != doc.version
        ]
        if availables and self.availabilities[-1].available:
            prev_version = availables[-1]
            obsoletes = set(
                p.sub_id
                for p in self.exposed_and_hidden
                if prev_version in p.exposed_versions
            ) - set(p.sub_id for p in doc.iter_parts())
            for sub_id in obsoletes:
                part = latest_loaded.get(sub_id)
                if part.abstract.in_force is False and part.abstract.is_latest is False:
                    continue
                part.abstract.in_force = False
                part.abstract.is_latest = False
                part.save()
        self.save()

    @flushed
    def insert_unavailable(self, version, date_document, after=None):
        """If after is omitted, it shall just include this in behind the latest
        version.
        """
        if after is None:
            self.availabilities.append(
                dm.VersionAvailability(
                    version=version, date_document=date_document, available=False
                )
            )
        else:
            for i, availability in enumerate(self.availabilities):
                if availability.version == after:
                    break
            else:
                raise NotFoundError(
                    f"Document {self.id_local} with version {after}" f" does not exist."
                )
            self.availabilities.insert(
                i + 1,
                dm.VersionAvailability(
                    version=version, date_document=date_document, available=False
                ),
            )
        self.save()

    @flushed
    def remove_latest(self):
        """Removes given version from the index and
        updates the VersionsMap instance correspondingly."""
        # TODO: fix: is_latest, Article.abstract.version (per article), in_force
        latest = self.availabilities.pop()
        if len(self.availabilities) == 0:
            return self.purge()
        removables = []
        for k, eh in enumerate(self.exposed_and_hidden):
            if eh.exposed_versions == [latest.version]:
                removables.append(k)
                try:
                    dm.delete(
                        "-".join(
                            (self.domain, self.id_local, eh.sub_id, latest.version)
                        )
                    )
                except NotFoundError:
                    # seems like this document was not actually loaded
                    pass
            elif eh.exposed_versions[-1] == latest.version:
                eh.exposed_versions.pop()
        for k in sorted(removables, reverse=True):
            self.exposed_and_hidden.pop(k)
        self.save()

    @flushed
    def purge(self):
        """Removes all document versions from the index and
        then deletes the VersionMap instance."""
        dm.Search().filter("term", abstract__id_local=self.id_local).filter(
            "term", abstract__domain=self.domain
        ).delete()
        dm.delete(self.meta.id)

    def iter_atoms(self):
        s = (
            dm.Search()
            .filter("term", abstract__id_local=self.id_local)
            .filter("term", abstract__domain=self.domain)
        )
        for hit in s.scan():
            yield hit

    @property
    def in_force(self):
        values = set(
            hit.abstract.in_force
            for hit in self.iter_atoms()
            if self.latest_available in hit.abstract.version
        )
        if len(values) == 1:
            return values.pop()
        else:
            raise ValueError(
                f"Document {self.domain}-{self.id_local} has "
                f"inconsistent in_force values."
            )

    @in_force.setter
    @flushed
    def in_force(self, value):
        @retry(ConnectionTimeout, 3, 30)
        def set_in_force_for_id(did):
            d = dm.GenericContentDocument.get(did)
            if d.doc_type in dm.content_document_types:
                if getattr(d.abstract, "in_force", None) == value:
                    return
                d.abstract.in_force = value
                d.save()

        ids = [
            hit.meta.id
            for hit in self.iter_atoms()
            if (self.latest_available in hit.abstract.version) or not value
        ]
        for id_ in ids:
            set_in_force_for_id(id_)

    def sub_id_change(self, version):
        """Iterates over every article, indicating, whether it was
         - newly inserted 'insert'
         - changed 'update'
         - removed 'delete'
        with respect to the previous version.
        """
        availables = [a.version for a in self.availabilities if a.available]
        if version not in availables:
            pass
        elif availables.index(version) == 0:
            handleds = set()
            for eh in self.exposed_and_hidden:
                if eh.sub_id in handleds:
                    continue
                handleds.add(eh.sub_id)
                if art_sub_id(eh.sub_id) and version in eh.exposed_versions:
                    yield eh.sub_id, "insert"
        else:
            prev = availables[availables.index(version) - 1]
            e2h = self.exposed_to_hidden
            handleds = set()
            for eh in self.exposed_and_hidden:
                if eh.sub_id in handleds:
                    continue
                handleds.add(eh.sub_id)
                if not art_sub_id(eh.sub_id):
                    continue
                hidden_vers = e2h.get((eh.sub_id, version))
                hidden_prev = e2h.get((eh.sub_id, prev))
                if hidden_vers == hidden_prev:  # both None or both the same
                    continue
                if hidden_vers is None:
                    yield eh.sub_id, "delete"
                elif hidden_prev is None:
                    yield eh.sub_id, "insert"
                else:
                    yield eh.sub_id, "update"
