#!/bin/bash
yum update -y
amazon-linux-extras install nginx1

domainEndpoint=$1

cd /etc/nginx/conf.d
cat <<EOF > default.conf
server {
  listen 8081;
  server_name localhost;
  
  location / {
    proxy_pass https://$domainEndpoint;
  }
}
EOF

systemctl enable nginx >> /home/ec2-user/userdata.log
systemctl start nginx >> /home/ec2-user/userdata.log

echo 'initialization completed' >> /home/ec2-user/userdata.log




