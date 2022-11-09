from collections import defaultdict

from legislative_act import model as dm


s = dm.Search().filter("term", doc_type="nationalreference")


popables = defaultdict(list)
deletables = set()

for hit in s.scan():
    if "§" not in hit.text:
        continue
    for k, target in enumerate(hit.references):
        if target.count("-") == 1:
            popables[hit.meta.id].append(k)
    if len(hit.references) == len(popables[hit.meta.id]):
        popables.pop(hit.meta.id)
        deletables.add(hit.meta.id)

for m_id, pops in popables.items():
    nr = dm.NationalReference.get(m_id)
    for k in list(reversed(pops)):
        nr.references.pop(k)
    nr.save()

for m_id in deletables:
    dm.delete(m_id)
