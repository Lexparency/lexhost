#!/usr/bin/env bash
set -e  # Abort on any error


echo -e "\n Uploading example documents. "
for id_local in 32002R0006 32009L0065 32013R0575 32016R0679
 do
 curl -XPOST localhost:5000/eu/${id_local}/initial/ -H "Content-type: text/html; charset=UTF-8" -d @legislative_act/tests/data/${id_local}-initial.html
done
curl -XPOST localhost:5000/eu/32016R0679/20180301/ -H "Content-type: text/html; charset=UTF-8" -d @legislative_act/tests/data/32016R0679-20180301.html
