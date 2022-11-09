from datetime import date
from elasticsearch import Elasticsearch

from legislative_act import model as dm

es = Elasticsearch(timeout=60 * 60)

index_name_orig = dm.index_name
dm.index_name = "{}1-{}".format(*dm.index_name.split("-"))
dm.index._name = dm.index_name

dm.index.create()

print(f"Start reindexing", flush=True)
es.reindex(body={"source": {"index": index_name_orig}, "dest": {"index": dm.index_name}})
print("done", flush=True)

version = date.today().strftime("%Y%m%d")

es.snapshot.create_repository(
    dm.index_name,
    body={"type": "fs", "settings": {"location": dm.index_name, "compress": True}},
)

print("Creating shapshot.", flush=True)
es.snapshot.create(
    dm.index_name,
    version,
    body={
        "indices": dm.index_name,
        "ignore_unavailable": True,
        "include_global_state": False,
    },
)
print("done.", flush=True)

print(
    f"""
Just shot a snap. Worked out fine!
Have a look via:
> es.sh GET /_snapshot/{dm.index_name}/{version}
Restore this snapshot using:
> es.sh POST /_snapshot/{dm.index_name}/{version}/_restore
"""
)
