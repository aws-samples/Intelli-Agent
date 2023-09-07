import { NestedStack, StackProps, RemovalPolicy, Duration } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as iam from 'aws-cdk-lib/aws-iam';
import * as api from 'aws-cdk-lib/aws-apigateway';
import * as glue from '@aws-cdk/aws-glue-alpha';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import path from "path";

interface etlStackProps extends StackProps {
    _domainEndpoint: string;
    _subEmail: string;
}

export class EtlStack extends NestedStack {
    _sfnOutput;

    constructor(scope: Construct, id: string, props: etlStackProps) {
        super(scope, id, props);

        // Creata glue job to process files speicified in s3 bucket and prefix
        const glueJob = new glue.Job(this, 'PythonShellJob', {
            executable: glue.JobExecutable.pythonShell({
              glueVersion: glue.GlueVersion.V1_0,
              pythonVersion: glue.PythonVersion.THREE,
              script: glue.Code.fromAsset(path.join(__dirname, 'scripts/scripts.py')),
            }),
            maxConcurrentRuns:200,
            maxRetries:3,
            // connections:[connection],
            maxCapacity:1,
            defaultArguments:{
                '--aos-endpoint':props._domainEndpoint,
                '--additional-python-modules': 'langchain==0.0.283,beautifulsoup4==4.12.2'
            }
          });

        glueJob.role.addToPrincipalPolicy(
            new iam.PolicyStatement({
                actions: [ 
                    "s3:List*",
                    "s3:Put*",
                    "s3:Get*",
                ],
                effect: iam.Effect.ALLOW,
                resources: ['*'],
            })
        )

        // Create SNS topic and subscription to notify when glue job is completed
        const topic = new sns.Topic(this, 'etl-topic', {
            displayName: 'etl-topic',
            topicName: 'etl-topic',
        });
        topic.addSubscription(new subscriptions.EmailSubscription(props._subEmail));

        // Create Step Function to orchestrate the glue job to start from API Gateway inovcation with S3 bucket and prefix
        const startState = new sfn.Pass(this, 'StartState', {
            result: sfn.Result.fromObject({
                "bucket": sfn.JsonPath.stringAt('$.bucket'),
                "prefix": sfn.JsonPath.stringAt('$.prefix'),
                "topicArn": topic.topicArn,
            }),
            resultPath: '$.input',
        });

        // // Glue task for file validation
        // const validateTask = new tasks.GlueStartJobRun(this, 'ValidateTask', {
        //     glueJobName: 'validate',
        //     integrationPattern: sfn.IntegrationPattern.RUN_JOB,
        // });

        // // Glue task for file processing
        // const processTask = new tasks.GlueStartJobRun(this, 'ProcessTask', {
        //     glueJobName: 'process',
        //     integrationPattern: sfn.IntegrationPattern.RUN_JOB,
        // });

        // Notify the result of the glue job
        const notifyTask = new tasks.SnsPublish(this, 'NotifyTask', {
            integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
            topic: topic,
            message: sfn.TaskInput.fromText(`Glue job ${glueJob.jobName} completed!`),
        });

        const sfnDefinition = startState
            // .next(validateTask)
            // .next(processTask)
            .next(notifyTask);
        
        const sfnStateMachine = new sfn.StateMachine(this, 'ETLState', {
            // definition: sfnDefinition,
            definitionBody: sfn.DefinitionBody.fromChainable(sfnDefinition),
            stateMachineType: sfn.StateMachineType.EXPRESS,
            timeout: Duration.minutes(30),
        });

        // Export the Step function to be used in API Gateway
        this._sfnOutput = sfnStateMachine;
    }
}