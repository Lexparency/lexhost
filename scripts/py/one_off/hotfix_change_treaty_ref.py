import re
from legislative_act import model as dm

from settings import INTERNET_DOMAIN

pattern = re.compile(
    f"(?P<trunc>http://{INTERNET_DOMAIN}/eu/[A-Z]+/)(?P<version>[0-9]+)$"
)

s = dm.Search()
s = s.filter("term", doc_type="cover")

locators = [c.meta.id for c in s.scan()]


for locator in locators:
    c = dm.Cover.get(locator)
    changed = False
    for base in c.based_on:
        href = pattern.sub("\g<trunc>", base.href)
        if href != base.href:
            print(f"Changeing: {base.href} -> {href}")
            base.href = href
            changed = True
    if changed:
        c.save()
