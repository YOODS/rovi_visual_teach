#!/bin/bash

CATKIN_WS=${PWD%src*}

source /opt/ros/kinetic/setup.bash
source $CATKIN_WS/devel/setup.bash

#installing aravis library
sudo apt-get install automake intltool
sudo apt-get install libgstreamer*-dev
cd ~
wget http://ftp.gnome.org/pub/GNOME/sources/aravis/0.6/aravis-0.6.4.tar.xz
tar xvf aravis-0.6.4.tar.xz
cd aravis-0.6.4
./configure
make
sudo make install
if ! grep /usr/local/lib /etc/ld.so.conf
then
    echo "
#Added by rovi/Install.sh
/usr/local/lib
" | sudo tee -a /etc/ld.so.conf
    sudo ldconfig
fi

#installing Eigen
sudo apt-get install libeigen3-dev

#installing nodejs and packages
cd ~
curl -sL https://deb.nodesource.com/setup_10.x | sudo -E bash -
sudo apt-get install nodejs
npm install rosnodejs
npm install js-yaml
npm install mathjs
npm install terminate --save
npm install ping

#installing python package
sudo apt install python-pip
pip install pip==9.0.3
pip install numpy==1.15.0 --user
pip install scipy --user
pip install wheel --user
pip install ipython==5.7 --user
pip install ipykernel==4.10 --user
pip install open3d-python --user

#installing X-Tile
cd ~
git clone https://github.com/YOODS/x-tile.git
cd x-tile
./create_debian_package.sh
cd ..
sudo dpkg -i x-tile_3.3-0_all.deb

#checkout rovi
cd $CATKIN_WS/src
git clone -b devel https://github.com/YOODS/rovi.git

#checkout rovi_utils
cd $CATKIN_WS/src
git clone -b devel https://github.com/YOODS/rovi_utils.git

#checkout rovi_industrial
cd $CATKIN_WS/src
git clone -b dev2101 https://github.com/YOODS/rovi_industrial.git

#checkout rtk_tools
cd $CATKIN_WS/src
git clone -b dev2101 https://github.com/YOODS/rtk_tools.git
sudo apt install python-tk
pip install tkfilebrowser --user
