import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";

/**
 * Create basic lambda policy.
 *
 * @param construct
 * @returns
 */
export function createBasicLambdaPolicy(): iam.PolicyDocument {
    return new iam.PolicyDocument({
        statements: [
            new iam.PolicyStatement({
                actions: ["logs:CreateLogGroup", "logs:CreateLogStream"],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:logs:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:log-group:/aws/lambda/*`
                ]
            }),
            new iam.PolicyStatement({
                actions: ["logs:PutLogEvents"],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:logs:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:log-group:/aws/lambda/*:log-stream:*`
                ]
            })
        ]
    });
}
