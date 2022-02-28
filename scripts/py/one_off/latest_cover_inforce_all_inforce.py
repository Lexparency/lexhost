from time import sleep

from elasticsearch import NotFoundError

from legislative_act import model as dm


def get_locators():
    s = dm.Search().filter('term', doc_type='versionsmap')
    priors1 = set(c.meta.id for c in s.scan() if len(c.availabilities) > 1)
    s = dm.Search().filter('term', doc_type='cover') \
        .filter('term', abstract__in_force=True) \
        .filter('term', abstract__is_latest=True)
    priors2 = set(f'{h.abstract.domain}-{h.abstract.id_local}' for h in s.scan())
    return priors1 & priors2


def align_single_cover_history(hid):
    vm = dm.VersionsMap.get(hid)
    versions = [a.version for a in vm.availabilities]
    for version in versions:
        c = dm.Cover.get(f'{hid}-COV-{version}')
        if not c.abstract.in_force:
            c.abstract.in_force = True
            c.save()


if __name__ == '__main__':
    locators = get_locators()
    print(f'Working through {len(locators)} locators.')
    for n, locator in enumerate(locators):
        if n % 1000 == 0 and n != 0:
            sleep(30)
        print(f'Saving changes for {locator}', flush=True)
        try:
            align_single_cover_history(locator)
        except NotFoundError:
            print(f'Could not handle {locator}')
