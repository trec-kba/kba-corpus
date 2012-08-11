
logfile=raw_bootstrap.log
exec > $logfile 2>&1

# get the modified version of file made by make below
wget --no-check-certificate https://s3.amazonaws.com/trec-kba-emr/emr-setup/custom-modules-setup

# setup openssl dev
sudo apt-get update
sudo apt-get -y install libssl-dev

# setup python 2.7 with ssl
wget http://python.org/ftp/python/2.7.2/Python-2.7.2.tar.bz2
tar jfx Python-2.7.2.tar.bz2
cd Python-2.7.2
./configure --with-threads --enable-shared
# activate socket and ssl in Modules/Setup{,.dist} 
cp ../custom-modules-setup Modules/Setup.dist
cp ../custom-modules-setup Modules/Setup
make
sudo make install
sudo ln -s /usr/local/lib/libpython2.7.so.1.0 /usr/lib/ 
sudo ln -s /usr/local/lib/libpython2.7.so /usr/ 


exit
