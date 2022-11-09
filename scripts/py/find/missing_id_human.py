from legislative_act import model as dm


s = dm.Search().filter("term", doc_type="cover")

result = set()

for hit in s.scan():
    try:
        ih = hit.id_human
    except AttributeError:
        result.add(hit.abstract.id_local)
    else:
        if ih == hit.abstract.id_local:
            result.add(hit.abstract.id_local)

print("\n".join(sorted(result)))


if __name__ == "__main__":
    print("Done")
