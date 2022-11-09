from datetime import date
from functools import lru_cache

from elasticsearch import NotFoundError
from elasticsearch_dsl import Q

from legislative_act import model as dm
from legislative_act.searcher import BasicSearcher


def popped(d, key):
    try:
        d.pop(key)
    except KeyError:
        pass
    return d


class SimpleHistory:
    def __init__(self, domain, id_local, availabilities: list, latest_cover_id):
        self.domain = domain
        self.id_local = id_local
        self.availabilities = availabilities
        self.latest_cover_id = latest_cover_id

    @property
    @lru_cache(maxsize=1)
    def in_force(self):
        if self.latest_cover_id is None:
            return None
        try:
            cover = dm.Cover.get(self.latest_cover_id)
        except NotFoundError:
            return None
        return cover.abstract.in_force

    def __repr__(self):
        return (
            f"SimpleHistory({self.domain}, " f"{self.id_local}, {self.availabilities})"
        )

    def to_dict(self):
        return {
            # 'domain': self.domain,  # excluded for now. It's "eu" anyway.
            "id_local": self.id_local,
            "in_force": self.in_force,
            "versions": [
                popped(a.to_dict(), "date_received") for a in self.availabilities
            ],
        }


class HistoryList(BasicSearcher):
    PAGE_SIZE = 100
    MAX_PAGES = 2000

    def __init__(self, only_availables=False):
        self.only_availables = only_availables
        super().__init__()

    def search(self):
        result = (
            dm.Search()
            .params(track_total_hits=True)
            .filter("term", doc_type="versionsmap")
        )
        if self.only_availables:
            result = result.query(
                "nested",
                path="availabilities",
                query=Q("term", availabilities__available=True),
            )
        return result

    def display_hit(self, hit) -> dict:
        try:
            availabilities = hit["availabilities"]
        except KeyError:
            availabilities = []
            latest_cover_id = None
        else:
            latest_version = availabilities[-1].version
            try:
                latest_cover_id = [
                    "-".join((hit.meta.id, "COV", i["hidden_version"]))
                    for i in hit["exposed_and_hidden"]
                    if i["sub_id"] == "COV" and latest_version in i["exposed_versions"]
                ][0]
            except IndexError:
                latest_cover_id = None
        return SimpleHistory(
            *hit.meta.id.split("-"),
            availabilities=availabilities,
            latest_cover_id=latest_cover_id,
        ).to_dict()

    def enhance_results(self, results, page=1):
        result = super().enhance_results(results, page)
        result["date"] = date.today().strftime("%Y-%m-%d")
        return result

    def scan(self):
        result = {
            "hits": [self.display_hit(hit) for hit in list(self.search().scan())],
            "date": date.today().strftime("%Y-%m-%d"),
        }
        result["total"] = len(result["hits"])
        return result


if __name__ == "__main__":
    import json

    hl = HistoryList()
    print(json.dumps(hl.get_page(1), indent=2))
    # print(hl.to_dict())
