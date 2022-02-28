from time import sleep

from legislative_act import model as dm


cids = [c.meta.id for c in dm.Search().filter('term', doc_type='cover').scan()]


# print('\n'.join(cids))

for k, cid in enumerate(cids):
    if k % 1000 == 0 and k != 0:
        sleep(30)
    cover = dm.Cover.get(cid)
    changed = False
    for anchor in cover.amended_by:
        if anchor.implemented is None:
            anchor.implemented = False
            changed = True
    if changed:
        print('Saving changes to ' + cid, flush=True)
        cover.save()


if __name__ == '__main__':
    print('done')
