import { CfnParameter } from "aws-cdk-lib";
import { Construct } from "constructs";

interface CdkParameters {
    s3ModelAssets: CfnParameter;
    subEmail: CfnParameter;
    openSearchIndex: CfnParameter;
    etlImageTag: CfnParameter;
    openSearchIndexDict: CfnParameter;
    etlImageName: CfnParameter;
}

export class DeploymentParameters implements CdkParameters {
    public s3ModelAssets: CfnParameter;
    public subEmail: CfnParameter;
    public openSearchIndex: CfnParameter;
    public etlImageTag: CfnParameter;
    public openSearchIndexDict: CfnParameter;
    public etlImageName: CfnParameter;

    constructor(scope: Construct) {
        this.s3ModelAssets = new CfnParameter(scope, "S3ModelAssets", {
            type: "String",
            description: "S3 Bucket for model & code assets",
        });

        this.subEmail = new CfnParameter(scope, "SubEmail", {
            type: "String",
            description: "Email address for SNS notification",
        });

        this.openSearchIndex = new CfnParameter(scope, "OpenSearchIndex", {
            type: "String",
            description: "OpenSearch index to store knowledge",
            default: "chatbot-index",
        });

        this.etlImageTag = new CfnParameter(scope, "ETLTag", {
            type: "String",
            description: "ETL image tag, the default is latest",
            default: "latest",
        });

        let OpenSearchIndexDictDefaultValue: string | undefined;

        if (process.env.AOSDictValue !== undefined) {
            OpenSearchIndexDictDefaultValue = process.env.AOSDictValue
        } else {
            OpenSearchIndexDictDefaultValue = '{"aos_index_mkt_qd":"aws-cn-mkt-knowledge","aos_index_mkt_qq":"gcr-mkt-qq","aos_index_dgr_qd":"ug-index-20240108","aos_index_dgr_qq":"gcr-dgr-qq", "aos_index_dgr_faq_qd":"faq-index-20240110", "dummpy_key":"dummpy_value"}';
        }

        this.openSearchIndexDict = new CfnParameter(scope, "OpenSearchIndexDict", {
            type: "String",
            description: "OpenSearch index to store knowledge dict format",
            default: OpenSearchIndexDictDefaultValue,
        });

        this.etlImageName = new CfnParameter(scope, "EtlImageName", {
            type: "String",
            description: "The ECR image name which is used for ETL, eg. etl-model",
        });
    }
}