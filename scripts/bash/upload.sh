#! /bin/bash

# Example usage:
# upload.sh /eu/32013R0575/initial/ 32013R0575.html

ENDPOINT=localhost:5000
REQUEST_PATH=$1
REQUEST_BODY=$2

CMD="curl -XPOST localhost:5000${REQUEST_PATH} -H \"Content-type: text/html; charset=UTF-8\""
CMD="${CMD} -d\"$(cat ${REQUEST_BODY})\""

# echo $CMD

result=$($CMD)
echo -e "\n$result"

