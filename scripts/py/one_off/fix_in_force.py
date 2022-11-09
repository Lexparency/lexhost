"""
The in_force flag of the abstract sub-object of the Article doc-type
should be set to False if the single Article it corresponds to was abrogated.
"""
from elasticsearch import NotFoundError

from legislative_act import model as dm

s = dm.Search()
s = s.filter("term", doc_type="versionsmap")


exforced = []
for hit in s.scan():
    availables = [a.version for a in hit.availabilities if a.available]
    if len(availables) <= 1:
        continue
    latest_available = availables[-1]
    for part in hit.exposed_and_hidden:
        if part.sub_id in ("PRE", "TOC", "COV") or part.sub_id.startswith("DEF_"):
            continue
        if latest_available not in part.exposed_versions:
            exforced.append(f"{hit.meta.id}-{part.sub_id}-{part.hidden_version}")

for id_ in exforced:
    try:
        art = dm.Article.get(id_)
    except NotFoundError:
        print(f"Could not find {id_}")
        continue
    if art.abstract.in_force is False:
        continue
    print(f"Adapting for {id_}")
    art.abstract.in_force = False
    art.save()
