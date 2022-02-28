es.sh PUT /_snapshot/legex-en '{"type": "fs", "settings": {"location": "legex-en", "compress": true}}'
es.sh GET /_snapshot
es.sh PUT /_snapshot/legex-en/20190918 '{"indices": "legex-en", "ignore_unavailable": true, "include_global_state": false}'
es.sh GET /_snapshot/legex-en/20190918 

# es.sh POST /_snapshot/legex-en/20190918/_restore
# es.sh GET /_cat/indices
