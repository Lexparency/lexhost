#! /bin/bash

curl -XGET localhost:9200/

ES_UP=$?

if [ $ES_UP -ne 0 ]
  then
  systemctl start elasticsearch.service
fi
