from legislative_act import model as dm

if __name__ == "__main__":
    s = dm.Search().filter("term", doc_type="versionsmap")
    ids = set()
    for hit in s.scan():
        ids.add(hit.meta.id)

    with open(f"{dm.index_name}.list", mode="w") as f:
        f.write("\n".join(ids))
