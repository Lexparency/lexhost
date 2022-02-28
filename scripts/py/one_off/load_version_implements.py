from collections import namedtuple, defaultdict
from time import sleep

from elasticsearch import NotFoundError

from legislative_act import model as dm
from settings import LANG_2, DEFAULT_IRI

LANG_2 = LANG_2.upper()


Impl = namedtuple('I', ['id_local', 'version', 'language', 'implements_ref'])


ims = defaultdict(list)
with open('tmp.list', encoding='utf-8') as f:
    for r in f.readlines():
        im = Impl(*r.strip().split(','))
        if im.language != LANG_2:
            continue
        href = im.implements_ref
        if href.startswith('/eu/'):
            href = DEFAULT_IRI + href
        ims[(im.id_local, im.version)].append(href)


for k, ((id_local, version), implements) in enumerate(ims.items()):
    if k % 1000 == 0 and k != 0:
        sleep(30)
    try:
        c = dm.Cover.get(f'eu-{id_local}-COV-{version}')
    except NotFoundError:
        continue
    changed = False
    for aname in c.iter_anchors():
        anchors = getattr(c, aname)
        for a in anchors:
            if a.href in implements:
                if a.implemented is not True:
                    changed = True
                    a.implemented = True
    if changed:
        print('changed: ' + ', '.join((id_local, version)), flush=True)
        c.save()
    else:
        print('Nothing to save for: ' + ', '.join((id_local, version)), flush=True)


if __name__ == '__main__':
    print('done')
