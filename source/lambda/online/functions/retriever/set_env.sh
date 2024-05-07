set -a
. /home/ubuntu/Project/llm-bot-dev/source/lambda/executor/.env
set +a
ps -ef | grep 443 | awk -F " " '{print $2}' | sudo xargs kill -9
sudo ssh -i /home/ubuntu/Project/llm-bot-dev/source/lambda/executor/llm-bot-atl.pem ec2-user@ec2-34-211-231-159.us-west-2.compute.amazonaws.com -Nf -L 443:vpc-domain66ac69e0-prbg1iy4iido-ksu2bpd7eblmz6buvk5viespdq.us-west-2.es.amazonaws.com:443
export AWS_PROFILE=atl-us-west-2
