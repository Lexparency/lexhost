#!/usr/bin/env bash
set -e  # Abort on any error


echo " Please enter a python executable (> 3.5.3) for setting up the virtual environment"
echo " (enter python executable)> "
read PYTHON_EXE
echo "Proceeding with $PYTHON_EXE"

virtualenv --python=$PYTHON_EXE venv

. ./venv/Scripts/activate


echo -e "\n Installing required packages\n ============================\n"
pip install -r requirements.txt

echo -e "\n This service requires elasticsearch to be running on port 9200 \n"


echo -e "\n Creating index\n ---------------------------\n"
python scripts/bash/create_index.py

mkdir LOG

echo -e "\n Running dev-server on the background (Logging to LOG/lexparency.log)"
echo -e " ------------------------------------\n"
python lexparency.py 1>LOG/lexparency.log 2>&1 &
echo " Process ID of that service:   " $!

echo -e "\n Uploading example documents. "
for id_local in 32002R0006 32009L0065 32013R0575 32016R0679
 do
 curl -XPOST localhost:5000/eu/${id_local}/initial/ -H "Content-type: text/html; charset=UTF-8" -d @legislative_act/tests/data/${id_local}-initial.html
done
curl -XPOST localhost:5000/eu/32016R0679/20180301/ -H "Content-type: text/html; charset=UTF-8" -d @legislative_act/tests/data/32016R0679-20180301.html


echo -e "\n\n  Now you browse through the test-documents under localhost:5000/."
echo "  I encourage you to use the bash script scripts/bash/es.sh"
echo "  for executing requests to elasticsearch for testing and debugging purposes."
