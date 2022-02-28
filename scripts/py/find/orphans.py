from sys import argv
from legislative_act import model as dm

s = dm.Search()
s = s.filter('term', abstract__id_local=argv[1])

for hit in s.scan():
    print(hit.meta.id, flush=True)
