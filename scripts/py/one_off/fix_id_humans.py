from time import sleep

from lexref.reflector import celex_2_id_human

from legislative_act import model as dm
from settings import LANG_2


cids = [h.meta.id for h in dm.Search().filter('term', doc_type='cover').scan()
        if h.abstract.id_local.startswith('3') and len(h.abstract.id_local) == 10]

for k, cid in enumerate(cids):
    if k % 1000 == 0 and k != 0:
        sleep(30)
    celex = cid.split('-')[1]
    id_human_fallback = celex_2_id_human(celex, LANG_2.upper())
    if id_human_fallback == celex:
        continue
    c = dm.Cover.get(cid)
    actual_id_human = getattr(c, 'id_human')
    if actual_id_human is not None:
        if actual_id_human.startswith(id_human_fallback.split()[0]):
            continue
    c.id_human = id_human_fallback
    c.save()
