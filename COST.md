# Cost Estimation

To deploy this asset, you will incur charges for the use of Amazon Web Services. The following data is based on the latest version published as of July 2024, deployed in the US East (N. Virginia) region (us-east-1), with a knowledge base built to operate 20 working days per month, consuming up to 4096 tokens per session. The cost estimate is based on the inference model anthropic.claude-3-sonnet.

## Model 1: Full deployment

<table>
  <tr>
    <th>Module</th>
    <th>Service</th>
    <th>Required</th>
    <th>price($/Mon)</th>
    <th>Note</th>
  </tr>
  <tr>
    <td rowspan="2">Console</td>
    <td>Amazon CloudFront</td>
    <td>Y</td>
    <td>0.00</td>
    <td>Starting from December 1, 2021, the first 1 TB of data transferred to the internet each month and 10 million HTTP/HTTPS requests from all edge locations will be free. <br><br>Data Transfer < 1TB
    </td>
  </tr>
  <tr>
    <td>Amazon S3</td>
    <td>Y</td>
    <td>0.13</td>
    <td rowspan="2">Visiting the UI 10 times per workday generates a combined size of 400MB for online and offline logs. The fixed asset size of the UI is 2.1MB. A 100MB PDF, after being split, generates approximately 300MB of S3 files. Adding the fixed assets of the model, which are 20.9GB, the total S3 usage per month is approximately 21.6GB. <br><br>S3 Standard Storage: 21.6GB<br>PUT Request: 1000/Mon.<br>SELECT Request: 10000/Mon.<br>RETURN/SCAN Data: 1GB/Mon. </td>
  </tr>
  <tr>
    <td rowspan="11">Core</td>
    <td>Amazon S3</td>
    <td>Y</td>
    <td>0.38</td>
  </tr>
   <tr>
    <td>Amazon Glue</td>
    <td>Y</td>
    <td>0.41</td>
    <td>Glue service Type：AWS Glue ETL jobs and interactive sessions<br>Costage： 1 DPU per job x 0.93 hours (3350 seconds)</td>
  </tr>
  <tr>
    <td>Amazon Sagemaker</td>
    <td>N</td>
    <td>37.12</td>
    <td>
    PDF:<br>SageMaker Type: SageMaker Asynchronous Inference<br>Instance Type: ml.g4dn.2xlarge<br><br>1 models / 1 models per endpoint = 1.00 endpoint(s)<br>endpoints rounded up by 1 (1.000000) = 1 endpoint(s) (rounded up)<br>1 endpoint(s) x 1 instances per endpoint x 1.90 hours per day x 20 day per month = 38.00 instance hours per month<br>38.00 hours per month x 0.94 USD per hour instance cost = 35.72 USD (monthly On-Demand cost)<br>10 GB per month x 0.14 USD = 1.40 USD
    </td>
  </tr>
  <tr>
    <td>AWS Lambda</td>
    <td>Y</td>
    <td>0.00</td>
    <td>
    Architecture: x86_64 <br>requests: 20000/Mon.<br>The Lambda free tier includes 1M free requests per month and 400,000 GB-seconds of compute time per month.
    </td>
  </tr>
  <tr>
    <td>AWS Lambda</td>
    <td>Y</td>
    <td>0.00</td>
    <td>
    Architecture: x86_64 <br>requests: 20000/Mon.<br>The Lambda free tier includes 1M free requests per month and 400,000 GB-seconds of compute time per month.
    </td>
  </tr>
  <tr>
    <td>Amazon DynamoDB</td>
    <td>Y</td>
    <td>34.92</td>
    <td>
    Capacity mode: Provisioned(Read: 5 units Write: 5 units)<br>             2.91$/Table/Mon.<br>Table Nums: 12<br>Storage: 1GB 1.2KB/item
    </td>
  </tr>
  <tr>
    <td>Amazon Opensearch</td>
    <td>Y</td>
    <td>1,013.34</td>
    <td>
       Availability Zone(s): 2-AZ without standby<br>
       Instance type: r6g.2xlarge.search<br>
       Number of data nodes: 2<br>Cost: 976.74 USD<br><br>
       Storage type: EBS<br>
       EBS volume type: General Purpose (SSD) - gp3<br>
       EBS volume size (GiB): 300<br>
       Provisioned IOPS: 3000 IOPS<br>
       Provisioned Throughput (MiB/s): 250 MiB/s<br>
       Cost: 36.60 USD
    </td>
  </tr>
  <tr>
    <td>Amazon Cognito</td>
    <td>Y</td>
    <td>69.25</td>
    <td>
       1,000 SAML or OIDC federation MAUs - 50 free SAML or OIDC federation MAUs per month = 950.00 billable SAML or OIDC federation<br> MAUsMax (950.00 billable SAML or OIDC federation MAUs, 0 minimum billable SAML or OIDC federation MAUs) = 950 total billable SAML or OIDC federation MAUs950 MAUs x 0.015 USD = 14.25 USD (SAML or OIDC federation MAUs)<br>
       SAML or OIDC federation cost (monthly): 14.25<br>
       $100 MAUs + 1,000 SAML or OIDC federation MAUs = 1,100.00 total billable MAUs1,100.00 MAUs x 1 Advanced security features option enabled = 1,100.00 Advanced security feature MAUs<br>
       Tiered price for: 1,100.00 MAUs1,100 MAUs x 0.05 USD = 55.00 USDTotal tier cost = 55.00 USD (ASF MAUs)Advanced security feature cost (monthly): 55$<br>
       55 USD + 14.25 USD = 69.25 USD
    </td>
  </tr>
  <tr>
    <td>Amazon API Gateway</td>
    <td>Y</td>
    <td>0.19</td>
    <td>
       REST API: 1,000 requests per month, no caching.<br>
       WebSocket API: 1,000 connections per day, 5,000 messages per day, average message size 32 KB, average connection duration 300 seconds<br><br>
       Total cost: 0.19$.
    </td>
  </tr>
  <tr>
    <td>AWS Step Functions</td>
    <td>Y</td>
    <td>0.28</td>
    <td>
       Workflow Number: 1000<br>
       Transition Number per workflow: 15 State
    </td>
  </tr>
  <tr>
    <td>Amazon ECR</td>
    <td>Y</td>
    <td>0.30</td>
    <td>
       3GB No Cross Region
    </td>
  </tr>
  <tr>
    <td>Amazon CloudWatch</td>
    <td>Y</td>
    <td>5.00</td>
    <td>
       10GB/Month
    </td>
  </tr>
  <tr>
    <td>LLM</td>
    <td>Amazon Bedrock</td>
    <td>Y</td>
    <td>8.20</td>
    <td>
      LLM Model<br>
      10,000,000 input tokens / 1000 = 10,000.00 K input tokens<br>
      10,000.00 K input tokens x 0.0002 USD per K-tokens = 2.00 USD per Month for input tokens<br>
      10,000,000 output tokens / 1000 = 10,000.00 K output tokens<br>
      10,000.00 K output tokens x 0.0006 USD per K-tokens = 6.00 USD per Month for output tokens<br>
      2.00 USD + 6.00 USD = 8.00 USD per Month for Express<br>
      Total On demand Cost for Express : 8.00 USD<br><br>
      Embedding Model:<br>
      10,000,000 input tokens / 1000 = 10,000.00 K input tokens<br>
      10,000.00 K input tokens x 0.00002 USD per K-tokens = 0.20 USD per Month for input token<br>
      Total On demand Cost for Titan Text Embeddings V2 (monthly): 0.20 USD
    </td>
  </tr>
  <tr>
    <td>Total</td>
    <td></td>
    <td></td>
    <td>1169.52</td>
    <td></td>
  </tr>
</table>




## Model 2: Online chat core deployent