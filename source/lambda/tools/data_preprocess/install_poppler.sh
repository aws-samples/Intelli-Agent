sudo apt-get update
sudo apt install libopenjp2-7-dev -y
sudo apt-get install cmake libblkid-dev e2fslibs-dev libboost-all-dev libaudit-dev -y
sudo apt-get install libnss3 libnss3-dev -y 
sudo apt-get install libcairo2-dev libjpeg-dev libgif-dev -y

wget https://poppler.freedesktop.org/poppler-21.09.0.tar.xz
tar -xvf poppler-21.09.0.tar.xz
cd poppler-21.09.0/
mkdir build
cd build/
cmake  -DCMAKE_BUILD_TYPE=Release   \
       -DCMAKE_INSTALL_PREFIX=/usr  \
       -DTESTDATADIR=$PWD/testfiles \
       -DENABLE_UNSTABLE_API_ABI_HEADERS=ON \
       ..
make 
sudo make install