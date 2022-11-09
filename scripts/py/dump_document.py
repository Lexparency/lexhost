from sys import argv
import json

from legislative_act import model as dm


domain = argv[1]
id_local = argv[2]

base = f"{domain}-{id_local}"

vm = dm.GenericContentDocument.get(base)

print(json.dumps(vm.as_dump()))

for eah in vm.exposed_and_hidden:
    d = dm.GenericContentDocument.get(f"{base}-{eah.sub_id}-{eah.hidden_version}")
    print(json.dumps(d.as_dump()))
