#!/bin/bash
sudo yum update -y
# Install common development tools
sudo yum groupinstall "Development Tools" -y
# Install Python and pip
sudo yum install python3 -y
sudo yum install python3-pip -y
# Install Node.js and npm
node_version="v22.11.0"
file_name="node-${node_version}-linux-x64"
wget "https://nodejs.org/dist/${node_version}/${file_name}.tar.xz"
sudo tar xvf "${file_name}.tar.xz" --directory=/usr/local
sudo mv "/usr/local/${file_name}" /usr/local/nodejs
sudo ln -sf /usr/local/nodejs/bin/node /usr/bin/node
sudo ln -sf /usr/local/nodejs/bin/npm /usr/bin/npm
sudo ln -sf /usr/local/nodejs/bin/npx /usr/bin/npx
# Install AWS CLI
pip3 install awscli
# Install Docker
sudo yum install docker -y
sudo service docker start
sudo usermod -aG docker ec2-user
sudo groupadd docker
sudo usermod -aG docker $USER
sudo chmod 666 /var/run/docker.sock

# Install TypeScript globally
sudo npm install -g typescript
# Additional dependencies or packages can be installed as needed.
# Start Docker service on boot
sudo chkconfig docker on
# Display installed versions
echo "Installed versions:"
echo "Python $(python3 --version)"
echo "Node.js $(node --version)"
echo "npm $(npm --version)"
echo "Docker $(docker --version)"
# echo "TypeScript $(tsc --version)"
# End of user data script

echo "Create service linked role for Amazon Opensearch Service"
# aws iam create-service-linked-role --aws-service-name es.amazonaws.com 2> /dev/null
aws iam create-service-linked-role --aws-service-name opensearchservice.amazonaws.com
