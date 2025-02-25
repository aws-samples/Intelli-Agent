/**
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 *  with the License. A copy of the License is located at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */

import { LambdaIntegration } from 'aws-cdk-lib/aws-apigateway';
import { Function, Code, Runtime, LayerVersion, Alias } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import * as apigw from "aws-cdk-lib/aws-apigateway";
import path from 'path';
import { Duration } from 'aws-cdk-lib';

export interface AuthHubProps {
  readonly solutionName: string;
  readonly apiGateway: apigw.RestApi
}

  /**
   * Construct to integrate auth assets
   */

  export class AuthHub extends Construct {
    
    // public apigw: RestApi;
    constructor(scope: Construct, id: string, props: AuthHubProps) {
        super(scope, id);
        
        const {solutionName, apiGateway} = props;
        const authLayer = new LayerVersion(
          this,
          "APILambdaAuthLayer",
          {
            code: Code.fromAsset(
              path.join(__dirname, "../../lambda"),
              {
                bundling: {
                  image: Runtime.PYTHON_3_12.bundlingImage,
                  command: [
                    "bash",
                    "-c",
                    `
                    echo "Starting bundling...";\
                    echo "Working directory: $(pwd)";\
                    ls -l;\
                    chmod -R 777 /asset-output;\
                    pip install -r requirements.txt -t /asset-output/python;\
                    echo "Bundling complete.";
                    `,
                  ],
                },
              },
            ),
            compatibleRuntimes: [Runtime.PYTHON_3_12],
            description: `Auth-Hub - API layer`,
          },
        )

        const authFunction = new Function(this, `${solutionName}AuthFunction`, {
          runtime: Runtime.PYTHON_3_12,
          code: Code.fromAsset('../../lambda'),
          handler: 'auth_api.handler',
          memorySize: 4096,
          timeout: Duration.seconds(10),
          // environment: {
          //   cognito_client_id: userPoolClient?.userPoolClientId,
          //   user_pool_id: userPool?.userPoolId,
          //   cognito_domain: userPoolDomain.domainName,
          //   region: props.region
          // }, 
          layers: [authLayer]
        });

        // authFunction.node.addDependency(userPoolClient)

        const version = authFunction.currentVersion;
        new Alias(this, 'AuthFunctionAlias', {
            aliasName: 'AuthFunctionAlias',
            version,
            provisionedConcurrentExecutions: 2,
        });
    
        // this.apigw = new RestApi(this, `${solutionName}AuthAPI`, {
        //   restApiName: `${solutionName}AuthAPI Service`,
        //   endpointConfiguration: {
        //     types: [EndpointType.REGIONAL],
        //   },
        //   defaultCorsPreflightOptions: {
        //     allowHeaders: [
        //       "Content-Type",
        //       "X-Amz-Date",
        //       "Authorization",
        //       "OIDC-Issuer",
        //       "X-Api-Key",
        //       "X-Amz-Security-Token",
        //     ],
        //     allowMethods: Cors.ALL_METHODS,
        //     allowCredentials: true,
        //     allowOrigins: Cors.ALL_ORIGINS,
        //   },
        //   deployOptions:{
        //     stageName: stage,
        //     loggingLevel: MethodLoggingLevel.INFO,
        //     dataTraceEnabled: true,
        //     metricsEnabled: true
        //   }
        // });
        const authIntegration = new LambdaIntegration(authFunction)
        const authResource = apiGateway.root.addResource('auth')
        const loginResource = authResource.addResource('login')
        loginResource.addMethod('POST', authIntegration);
        const tokenResource = authResource.addResource('token')
        const verifyResource = tokenResource.addResource('verify');
        verifyResource.addMethod('GET', authIntegration);
        const refreshResource = tokenResource.addResource('refresh');
        refreshResource.addMethod('POST', authIntegration);

        // const configFile = 'auth.json';
        // new AwsCustomResource(this, 'WebConfig', {
        //   logRetention: RetentionDays.ONE_DAY,
        //   onUpdate: {
        //     action: 'putObject',
        //     parameters: {
        //       Body: JSON.stringify({
        //         api_url: this.apigw.url,
        //         app_url: props.distribution.distributionDomainName,
        //       }),
        //       Bucket: props.portalBucket.bucketName,
        //       CacheControl: 'max-age=0, no-cache, no-store, must-revalidate',
        //       ContentType: 'application/json',
        //       Key: configFile,
        //     },
        //     service: 'S3',
        //     physicalResourceId: PhysicalResourceId.of(`config-${randomTag}`),
        //   },
        //   policy: AwsCustomResourcePolicy.fromStatements([
        //     new PolicyStatement({
        //       actions: ['s3:PutObject'],
        //       resources: [props.portalBucket.arnForObjects(configFile)]
        //     })
        //   ])
        // });
      }
  }
  