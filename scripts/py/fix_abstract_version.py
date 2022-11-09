from typing import Union

from elasticsearch import NotFoundError

from legislative_act import model as dm

s = dm.Search()
s = s.filter("term", doc_type="versionsmap")


c2v = {}
for hit in s.scan():
    if len(hit.availabilities) == 1:
        continue
    for part in hit.exposed_and_hidden:
        if len(part.exposed_versions) == 1:
            continue
        c2v[
            f"{hit.meta.id}-{part.sub_id}-{part.hidden_version}"
        ] = part.exposed_versions


def get_doc(
    id_,
) -> Union[dm.Article, dm.Cover, dm.ContentsTable, dm.Definition, dm.Preamble]:
    sub_id = id_.split("-")[2]
    if sub_id.startswith("DEF"):
        return dm.Definition.get(id_)
    if sub_id == "TOC":
        return dm.ContentsTable.get(id_)
    if sub_id == "COV":
        return dm.Cover.get(id_)
    if sub_id == "PRE":
        return dm.Preamble.get(id_)
    return dm.Article.get(id_)


for id_, versions in c2v.items():
    try:
        art = get_doc(id_)
    except NotFoundError:
        print(f"Could not find {id_}")
        continue
    if art.abstract.version == versions:
        continue
    print(f"Fixing abstract.version for {id_}", flush=True)
    art.abstract.version = versions
    art.save()
