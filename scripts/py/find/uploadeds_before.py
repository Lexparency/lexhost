from sys import argv
from datetime import datetime, date

from elasticsearch_dsl import Q

from legislative_act import model as dm

try:
    day = datetime.strptime(argv[1], "%Y-%m-%d")
except IndexError:
    day = date.today()

s = dm.Search().query(
    "nested",
    path="availabilities",
    query=Q(
        "range", availabilities__date_received={"gte": date(2000, 1, 1), "lte": day}
    ),
)

for hit in s.scan():
    print(hit.meta.id)


if __name__ == "__main__":
    print("Done")
