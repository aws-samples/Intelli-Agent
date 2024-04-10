Follow step below to create a ec2 instance with nginx installed

## 2.1. Prepare the environment

```bash
# display image id with ubuntu 20.04 from aws
aws ec2 describe-images --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*" "Name=owner-id,Values=09972010****" --region us-west-2 --query 'Images[0].ImageId' --output text

# list default vpc id
aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[*].{ID:VpcId}' --output text

# list all security groups bonded to default vpc
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=vpc-ad29afd5" --query 'SecurityGroups[*].{Name:GroupName,ID:GroupId}' --output text

# list all public subnets bonded to default vpc
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-ad29afd5" "Name=map-public-ip-on-launch,Values=true" --query 'Subnets[*].{Name:SubnetId}' --output text

# list all availability pem keys
aws ec2 describe-key-pairs --query 'KeyPairs[*].{Name:KeyName}' --output text

# create a ec2 with ubuntu 20.04 and install nginx through userdata, the ip address will be passed as input parameter to userdata
aws ec2 run-instances --image-id ami-01cb61d12413ba783 --count 1 --instance-type t2.micro --key-name us-west-2 --security-group-ids sg-0ceb6e950b89e8f69 --subnet-id subnet-b42915ff --user-data file://nginx.sh --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ec2Endpoint}]' --query 'Instances[*].{ID:InstanceId,IP:PublicIpAddress}' --output text
```

## 2.2. lanuch the flask app

```bash
export FLASK_APP=app.py  # Replace 'app.py' with the name of your Flask app file if it's different
python -m flask run --host=0.0.0.0 --port=5000
```

login the app with address similar to http://<ec2 public ip>:5000/predict to check if the app is running. Modify the inference.py to check the actual output, for now it will just hint "Did not attempt to load JSON data because the request Content-Type was not 'application/json'" since we are not passing any data to the app.
