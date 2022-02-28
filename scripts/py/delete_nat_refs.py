from legislative_act import model as dm


s = dm.Search().filter('term', doc_type='nationalreference')

ids = [d.meta.id for d in s.scan()]

for mid in ids:
    print('deleting ' + mid)
    dm.delete(mid)
