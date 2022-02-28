#! /bin/bash
set -e

INDEX=$1
DATE=$(date +%Y%m%d)
es.sh PUT /_snapshot/${INDEX}/${DATE} '{"indices": "${INDEX}", "ignore_unavailable": true, "include_global_state": false}'

sleep 2

es.sh GET /_snapshot/${INDEX}/${DATE}
