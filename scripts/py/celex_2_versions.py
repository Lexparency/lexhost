from legislative_act import model as dm

s = dm.Search()
s = s.filter("term", doc_type="versionsmap")

for hit in s.scan():
    celex = hit.meta.id.split("-")[1]
    versions = [a.version for a in hit.availabilities]
    print(f"{repr(celex)}: {repr(versions)}", flush=True)
