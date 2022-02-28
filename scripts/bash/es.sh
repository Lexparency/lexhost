#! /bin/bash

# es.sh GET eurlex-en/_search?q=type:cover

REQUEST_TYPE=$1
REQUEST_PATH=$(echo "$2"|cut -d\? -f1)
# shellcheck disable=SC2001
QUERY_PART=$(echo "$2"|sed 's/^[^?]*?\?//')
REQUEST_BODY=$3


if [ "$QUERY_PART" == "" ]
 then
  CMD="curl -X${REQUEST_TYPE} localhost:9200${REQUEST_PATH}?pretty "
 else
  CMD="curl -X${REQUEST_TYPE} localhost:9200${REQUEST_PATH}?${QUERY_PART}&pretty "
fi

if [ "${REQUEST_BODY}" != "" ]
 then
 if [ -f "${REQUEST_BODY}" ]
  then
   $CMD -H 'Content-Type: application/json' -d"$(cat "${REQUEST_BODY}")"
  else
   $CMD -H 'Content-Type: application/json' -d"${REQUEST_BODY}"
 fi
 else
  result=$($CMD)
  echo -e "$result"
fi
