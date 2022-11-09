"""
Some anchor texts are very strange ... like "?url=302%F200584"
Find them! Take them Down!
"""
from legislative_act import model as dm


printed = set()


for h in dm.Search().filter("term", doc_type="cover").scan():
    celex = h.meta.id.split("-")[1]
    if celex in printed:
        continue
    for ref in dm.Cover.iter_anchors():
        try:
            for a in h[ref]:
                if "uri=" in a["text"]:
                    print(celex)
                    printed.add(celex)
        except KeyError:
            continue
        if celex in printed:
            break


if __name__ == "__main__":
    print("Done")
