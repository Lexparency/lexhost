from legislative_act import model as dm
from legislative_act.history import DocumentHistory

s = dm.Search() \
    .filter('term', doc_type='cover') \
    .filter('term', abstract__in_force=True).filter()

repealed_enforced = set()
for hit in s.scan():
    try:
        rpb = hit.repealed_by
    except AttributeError:
        continue
    else:
        repealed_enforced.add(f"{hit.abstract.domain}-{hit.abstract.id_local}")


for path in repealed_enforced:
    dh = DocumentHistory.get(path)
    dh.in_force = False


if __name__ == '__main__':
    print('Done')
