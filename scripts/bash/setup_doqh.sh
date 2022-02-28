apt-get install tmux
apt-get install vim
apt-get install curl

apt-get install apache2
a2enmod ssl
a2enmod headers
a2enmod expires
a2enmod rewrite
systemctl restart apache2

echo "alias ls='ls --color=auto'" >> /etc/bash.bashrc
echo "alias development_rights='chown -R www-data:www . && find . -type d -exec chmod 770 {} + && find . -type f -exec chmod 660 {} +'" >> /etc/bash.bashrc
echo "alias production_rights='chown -R www-data:www . && find . -type d -exec chmod 550 {} + && find . -type f -exec chmod 440 {} +'" >> /etc/bash.bashrc
echo "PS1=\"\${debian_chroot:+(\$debian_chroot)}\\u@\\h:\\w [\\d - \\t] \\n\\$ \"" >> /etc/bash.bashrc

sed -i "s/\"syntax on/syntax on/" /etc/vim/vimrc
sed -i "s/\"set background=dark/set background=dark/" /etc/vim/vimrc
echo "set hlsearch!" >> /etc/vim/vimrc


apt-get install java-common openjdk-8-jre
cd /root/
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-7.x.list
apt-get update && apt-get install elasticsearch
/bin/systemctl daemon-reload
/bin/systemctl enable elasticsearch.service
vi /etc/elasticsearch/jvm.options
systemctl start elasticsearch.service



# Setting up the python environment
apt-get update
apt-get upgrade
apt-get install liblzma-dev
apt-get install -y make build-essential libssl-dev zlib1g-dev
apt-get install -y libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm
apt-get install -y libncurses5-dev  libncursesw5-dev xz-utils tk-dev
cd /usr/src/
wget https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tgz
tar xzvf Python-3.7.2.tgz
cd Python-3.7.2
ls
./configure --enable-optimizations --enable-shared  # enable-shared only for using it with wsgi
make
make install
export LD_LIBRARY_PATH=/usr/src/Python-3.7.2/  # enable-shared only for using it with wsgi
python3.7 -m pip install --upgrade pip


# WSGI
# (note: https://code.google.com/archive/p/modwsgi/wikis/QuickInstallationGuide.wiki#Configuring_The_Source_Code)
apt-get install apache2-dev
cd /usr/src/
wget https://github.com/GrahamDumpleton/mod_wsgi/archive/4.6.5.tar.gz
tar -xzvf 4.6.5.tar.gz
cd mod_wsgi-4.6.5
./configure --with-python=$(which python3.7)
make
make install
echo $LD_LIBRARY_PATH >> /etc/ld.so.conf
apt-get install virtualenv

# HINT: Don't use virtualenvs on the server. It's a pain!


# Letsencrypt
echo "deb http://ftp.debian.org/debian stretch-backports main" | tee -a /etc/apt/sources.list.d/stretch.list
apt-get update && apt-get install python-certbot-apache -t stretch-backports

# certbot certonly --authenticator standalone --pre-hook "systemctl stop apache2" --post-hook "systemctl start apache2"

echo -e "\n  You should set TimeoutStartSec in /usr/lib/systemd/system/elasticsearch.service to 300 (seconds)"
echo -e "  After that, run the command\n    > systemctl enable elasticsearch.service"

