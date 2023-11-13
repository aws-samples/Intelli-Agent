#!/bin/bash
# install nginx, flask and pytorch
apt update -y
apt install nginx -y
apt install python3-pip -y
pip3 install flask
pip3 install torch

# set up nginx reverse proxy
cd /etc/nginx/sites-available
cat <<EOF > default
server {
  listen 5000;
  server_name localhost;
  
  location /infer {
    proxy_pass http://127.0.0.1:5000;
  }
}
EOF

systemctl enable nginx
systemctl start nginx

echo 'initialization completed' >> /home/ubuntu/userdata.log

