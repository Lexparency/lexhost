#! /bin/bash
set -e
script=$1

if [ $script == "" ]
  then
  echo "No script provided"
  exit
else
  name=$(echo $script | sed 's#.\+\/##' | cut -d\. -f1)
  echo $name
  python3.7 $script 1> ${name}.log 2> ${name}.err &
fi
