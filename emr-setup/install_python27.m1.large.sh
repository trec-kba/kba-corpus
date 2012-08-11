#!/bin/bash
logfile=raw_bootstrap.log
exec > $logfile 2>&1

# setup openssl dev
sudo aptitude update
sudo aptitude -v -y install libssl-dev

# get the modified version of file made by make below
wget --no-check-certificate https://s3.amazonaws.com/trec-kba-emr/emr-setup/Python-2.7.2-compiled-aws-emr-m1.large.tar.gz
tar zfx Python-2.7.2-compiled-aws-emr-m1.large.tar.gz
cd Python-2.7.2
make
sudo make install
sudo ln -s /usr/local/lib/libpython2.7.so.1.0 /usr/lib/ 
sudo ln -s /usr/local/lib/libpython2.7.so /usr/ 
cd ..

hash -r
source ~/.bashrc

## install xz
sudo aptitude -v -y install xz-utils

# install boto
#wget http://boto.googlecode.com/files/boto-2.3.0.tar.gz
#tar xzf boto-2.3.0.tar.gz
#cd boto-2.3.0
#sudo python setup.py install
#cd ..

#cat > boto.cfg <<EOF
#[Credentials]
#aws_access_key_id = 
#aws_secret_access_key = 
#EOF

#sudo mv boto.cfg /etc/boto.cfg

# install mrjob, so we are sure that it gets done by the new python
wget --no-check-certificate https://s3.amazonaws.com/trec-kba-emr/emr-setup/mrjob-0.3.2.tar.gz
tar xzf mrjob-0.3.2.tar.gz
cd mrjob-0.3.2
sudo python setup.py install
cd ..

## install redis server and python library
#sudo aptitude -v -y install redis-server
#wget --no-check-certificate https://s3.amazonaws.com/trec-kba-emr/emr-setup/redis-2.4.11.tar.gz
#tar xzf redis-2.4.11.tar.gz
#cd redis-2.4.11
#sudo python setup.py install
#cd ..

#wget --no-check-certificate https://s3.amazonaws.com/trec-kba-emr/emr-setup/requests.tar.gz
#tar xzf requests.tar.gz
#cd kennethreitz-requests-775b6f6
#sudo python setup.py install
#cd ..

exit
