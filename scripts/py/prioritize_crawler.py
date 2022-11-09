from legislative_act import model as dm

s = dm.Search()
s = s.filter("term", doc_type="nationalreference")


counter = {}
for mid in [c.meta.id for c in s.scan()]:
    nr = dm.NationalReference.get(mid)
    try:
        dj_url = [u for u in nr.urls if "dejure.org" in u][0]
    except IndexError:
        continue
    counter[dj_url] = len(nr.references)

for url, rank in sorted(counter.items(), key=lambda x: x[1], reverse=True):
    if not url.endswith(".html"):
        print(url, rank)
