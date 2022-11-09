from legislative_act import model as dm

s = dm.Search()
s = s.filter("term", doc_type="cover").filter("term", abstract__is_latest=True)
for hit in s.scan():
    try:
        print(hit.id_human, end=" : ")
    except AttributeError:
        pass
    else:
        print(hit.title)
