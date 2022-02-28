TARGET=/home/martin/dev_data

mkdir $TARGET


while IFS= read -r id_local
  do
  if [ "$id_local" != "id_local" ]
    then
    python3.7 "${PYTHONPATH}"scripts/py/dump_document.py eu "$id_local" > "$TARGET"/"$id_local".jsons
    sleep 2
  fi
done < "${PYTHONPATH}"scripts/ids_local_dev.csv

tar -pczf /home/martin/dev_data.tar.gz $TARGET

rm -rf $TARGET
