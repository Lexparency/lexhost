#! /bin/bash

curl -XPOST localhost:5000$1 -H "Content-type: text/html; charset=UTF-8" -d @$2
