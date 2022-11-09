from time import sleep

from legislative_act import model as dm


cids = [
    h.meta.id
    for h in dm.Search().filter("term", doc_type="cover").scan()
    if "D" in h.abstract.id_local
]

for k, cid in enumerate(cids):
    if k % 1000 == 0 and k != 0:
        sleep(30)
    c = dm.Cover.get(cid)
    if "Beschluss" in c.title:
        continue
    if not c.id_human.startswith("Beschluss "):
        continue
    c.id_human = c.id_human.replace("Beschluss ", "Entscheidung ")
    c.save()
