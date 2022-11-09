from time import sleep
from legislative_act import model as dm

MAXLEN = 1000000

aids = [
    h.meta.id
    for h in dm.Search().filter("term", doc_type="article").scan()
    if len(h.body.stripped) > 1000000
]

print(aids)

for aid in aids:
    print(aid, flush=True)
    c = dm.Article.get(aid)
    c.body.stripped = c.body.stripped[:MAXLEN]
    c.save()
    sleep(15)


if __name__ == "__main__":
    print("Done")
