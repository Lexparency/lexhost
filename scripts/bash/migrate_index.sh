# Start via creating the new index
lang=$1
es.sh POST /_reindex '{"source": {"index": "legex-$lang"},"dest": {"index": "legex1-$lang"}}'
es.sh DELETE /legex-$lang
es.sh POST /_aliases '{"actions" : [{ "add" : {"index" : "legex1-$lang", "alias" : "legex-$lang"}}]}'
