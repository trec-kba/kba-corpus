#!/bin/bash
logfile=install_gevent.log
exec > $logfile 2>&1

#sudo touch /etc/apt/sources.list.d/backports.list 
#sudo chmod a+w /etc/apt/sources.list.d/backports.list 
#cat > /etc/apt/sources.list.d/backports.list <<EOF
#deb http://backports.debian.org/debian-backports squeeze-backports main
#EOF
#sudo apt-get update
#sudo aptitude -y install python-gevent

# setup greenlets
wget --no-check-certificate https://s3.amazonaws.com/trec-kba-emr/emr-setup/greenlet-0.3.3.tar.gz
tar zfx greenlet-0.3.3.tar.gz
cd greenlet-0.3.3
sudo python setup.py install
cd ..

# setup greenlets
wget --no-check-certificate https://s3.amazonaws.com/trec-kba-emr/emr-setup/gevent-0.13.6.tar.gz
tar zfx gevent-0.13.6.tar.gz
cd gevent-0.13.6
sudo python fetch_libevent.py
sudo python setup.py install

exit 