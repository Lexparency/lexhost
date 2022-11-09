from time import sleep

from legislative_act import model as dm


def get_locators():
    s = dm.Search()
    s = s.filter("term", doc_type="cover")
    return [c.meta.id for c in s.scan()]


def fix_single_cover(c: dm.Cover):
    changed = False
    for anchor in c.completed_by:
        if anchor.implemented is False:
            del anchor.implemented
            changed = True
    return changed


if __name__ == "__main__":
    locators = get_locators()
    print(f"Working through {len(locators)} locators.")
    for n, locator in enumerate(locators):
        if n % 1000 == 0 and n != 0:
            sleep(30)
        cover = dm.Cover.get(locator)
        if fix_single_cover(cover):
            print(f"Saving changes for {locator}", flush=True)
            cover.save()
