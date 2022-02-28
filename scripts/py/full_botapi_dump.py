import os
import re
import json
from time import sleep
from datetime import date

from elasticsearch import ConnectionTimeout

from legislative_act import model as dm

from views.dbmap import SimpleHistory
from bot_api import DocumentBot
from settings import DUMP_PATH


if not os.path.exists(DUMP_PATH):
    os.makedirs(DUMP_PATH)

s = dm.Search()
s = s.filter('term', doc_type='versionsmap')

relevant_celex_pattern = re.compile('^eu-3[0-9]{4}[DRLF][0-9]{4}$')

relevants = []

for hit in s.scan():
    try:
        availabilities = hit['availabilities']
    except KeyError:
        print(f"Trouble with {hit.meta.id}")
        continue
    if relevant_celex_pattern.match(hit.meta.id) is None:
        continue
    latest_version = availabilities[-1].version
    try:
        latest_cover_id = [
            '-'.join((hit.meta.id, 'COV', i['hidden_version']))
            for i in hit['exposed_and_hidden']
            if i['sub_id'] == 'COV'
            and latest_version in i['exposed_versions']][0]
    except IndexError:
        print(f"Trouble with {hit.meta.id}")
        continue
    relevants.append(SimpleHistory(*hit.meta.id.split('-'),
                                   availabilities=availabilities,
                                   latest_cover_id=latest_cover_id))


dumped = {f[3:-5] for f in os.listdir(DUMP_PATH)}

for sh in relevants:
    try:
        if sh.id_local in dumped:
            continue
    except ConnectionTimeout:
        print(f'Timeout Error for {sh.id_local}')
        continue
    sleep(1)
    # noinspection PyBroadException
    try:
        d = DocumentBot(sh.domain, sh.id_local).get(full=True)
    except Exception:
        print(f'Trouble dumping {sh.domain}-{sh.id_local}')
    else:
        with open(os.path.join(DUMP_PATH, f'{sh.domain}-{sh.id_local}.json'),
                  encoding='utf-8', mode='w') as f:
            json.dump(d, f)


if __name__ == '__main__':
    print('Done')
