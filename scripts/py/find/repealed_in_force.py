from time import sleep

from legislative_act import model as dm
from utils import get_document_history

inconsistents = set()

for h in (
    dm.Search()
    .filter("term", doc_type="cover")
    .filter("term", abstract__in_force=True)
    .scan()
):
    try:
        if h.repealed_by:
            inconsistents.add((h.abstract.domain, h.abstract.id_local))
    except AttributeError:
        continue

print("\n".join(sorted(map("-".join, inconsistents))))


for k, (domain, celex) in enumerate(inconsistents):
    dh = get_document_history(domain, celex)
    dh.in_force = False
    sleep(30)


if __name__ == "__main__":
    print("Done")
