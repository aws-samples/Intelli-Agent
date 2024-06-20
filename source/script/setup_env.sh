#!/bin/bash
sudo yum update -y
# Install common development tools
sudo yum groupinstall "Development Tools" -y
# Install Python and pip
sudo yum install python3 -y
sudo yum install python3-pip -y
# Install Node.js and npm
sudo yum install nodejs npm -y
# Install AWS CLI
pip3 install awscli
# Install Docker
sudo yum install docker -y
sudo service docker start
sudo usermod -aG docker ec2-user
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
echo "TypeScript $(tsc --version)"
# End of user data script

echo "Create service linked role for Amazon Opensearch Service"
aws iam create-service-linked-role --aws-service-name es.amazonaws.com 2> /dev/null
