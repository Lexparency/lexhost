set -e
domain=$(grep INTERNET_DOMAIN config/settings.py | head -n 1 | cut -d\' -f 2)

if [ -f /home/martin/lexparency.tar.gz ]
  then
  /usr/local/bin/python3.7 -m pip install --upgrade pip -q
  archive_number=$(($(ls -tr lex_archive/ | tail -n 1 | cut -d _ -f 2 | cut -d . -f 1) + 1))
  mv ${domain}/static/lexparency.tar.gz lex_archive/lexparency_${archive_number}.tar.gz
  echo -- removing the old version
  rm -rf ${domain}
  mv /home/martin/lexparency.tar.gz .
  tar -xzf lexparency.tar.gz
  mv lexparency "${domain}"
  chmod 444 ${domain}/settings.py
  chmod 555 ${domain}/scripts/bash/*.sh
  mv lexparency.tar.gz ${domain}/static/
  echo "Sitemap: https://${domain}/sitemap.xml" >> ${domain}/static/robots.txt
  pip3.7 install -q -r ${domain}/requirements.txt
  echo -- restarting apache
  systemctl reload apache2
  echo -- testing
  curl -XGET https://${domain}/ > /dev/null
  curl -XGET https://${domain}/sitemap.xml > /dev/null
  mv ${domain}/scripts/bash/update.sh config/
else
  echo -- nothing shipped :/
fi
