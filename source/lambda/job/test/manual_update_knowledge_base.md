### the first time you use manual injection
* prepare small ec2 instance to connect to aos

* prepare .env file and save as source/lambda/online/lambda_main/test/.env

### the first time you open a terminal
*  sudo ssh -i xxx.pem ec2-user@xxxx.amazonaws.com  -Nf -L 443:vpc-xxx.us-east-1.es.amazonaws.com:443

### every time you use manual injection

* modify path and files in source/lambda/job/test/run_update_common_knowledge_base.py (files = [xx])

* cd source/lambda/job

* python test/run_update_common_knowledge_base.py