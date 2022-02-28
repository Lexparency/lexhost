"""
see purpose of the is_latest flag.
"""
from collections import defaultdict
from typing import Union

from elasticsearch import NotFoundError

from legislative_act import model as dm

s = dm.Search()
s = s.filter('term', doc_type='versionsmap')

id_2_is_latest = {}
for hit in s.scan():
    availables = [a.version for a in hit.availabilities if a.available]
    if len(availables) <= 1:
        continue
    latest_available = availables[-1]
    s2v2vs = defaultdict(dict)
    for part in hit.exposed_and_hidden:
        id_2_is_latest[f"{hit.meta.id}-{part.sub_id}-{part.hidden_version}"] = \
            latest_available in part.exposed_versions


def get_doc(id_) -> Union[dm.Article, dm.Cover, dm.ContentsTable, dm.Definition, dm.Preamble]:
    sub_id = id_.split('-')[2]
    if sub_id.startswith('DEF'):
        return dm.Definition.get(id_)
    if sub_id == 'TOC':
        return dm.ContentsTable.get(id_)
    if sub_id == 'COV':
        return dm.Cover.get(id_)
    if sub_id == 'PRE':
        return dm.Preamble.get(id_)
    return dm.Article.get(id_)


for id_, is_latest in id_2_is_latest.items():
    try:
        doc = get_doc(id_)
    except NotFoundError:
        print(f"Could not find {id_}.")
        continue
    if doc.abstract.is_latest == is_latest:
        continue
    print(f"fixing is_latest for {id_}.", flush=True)
    doc.abstract.is_latest = is_latest
    doc.save()
