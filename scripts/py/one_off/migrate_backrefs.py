import json
from elasticsearch.exceptions import NotFoundError
from hashlib import sha1

from legislative_act import model as dm

from settings import LANG_2, BACKREF_DATA_PATH


class Nationals:
    def __init__(self, language):
        with open(BACKREF_DATA_PATH, encoding="utf-8") as f:
            data = [
                li["references"]
                for li in json.load(f)["data"]
                if li["language"] == language
            ][0]
        self.mapping = {
            (i["domain"], i["id_local"], i["sub_id"]): i["nationals"] for i in data
        }

    def __call__(self, domain, id_local, sub_id):
        return self.mapping.get((domain, id_local, sub_id), [])


n = Nationals(LANG_2)


for key, values in n.mapping.items():
    ref = "-".join(key if key[2] != "TOC" else key[:2])
    for value in values:
        for target in value["targets"]:
            meta_id = sha1(target["text"].encode("utf-8")).hexdigest()[10:20]
            try:
                nr = dm.NationalReference.get(meta_id)
            except NotFoundError:
                nr = dm.NationalReference(
                    country_name=value["country_name"],
                    text=target["text"],
                    urls=[pf["href"] for pf in target["platforms"]],
                    references=[],
                )
                nr.meta.id = meta_id
            if ref in nr.references:
                continue
            nr.references.append(ref)
            nr.save()
