from legislative_act import model as dm


s = dm.Search()
s = s.filter('term', doc_type='versionsmap')
for hit in s.scan():
    try:
        availabilities = hit['availabilities']
    except KeyError:
        availabilities = []
        latest_cover_id = None
    else:
        latest_version = availabilities[-1].version
        try:
            latest_cover_id = [i for i in hit['exposed_and_hidden']
                               if i['sub_id'] == 'COV'
                               and latest_version in i['exposed_versions']][0]
        except IndexError:
            print(hit.meta.id, flush=True)
