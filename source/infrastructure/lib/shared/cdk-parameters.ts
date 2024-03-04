import { CfnParameter, Environment } from 'aws-cdk-lib';
import { Construct } from 'constructs';

interface CdkParameters {
    _S3ModelAssets: CfnParameter;
    _SubEmail: CfnParameter;
    _OpenSearchIndex: CfnParameter;
    _OpenSearchIndexDict: CfnParameter;
}

interface CdkProps {
    env: any;
}

export class DeploymentParameters implements CdkParameters {
    _S3ModelAssets: CfnParameter;
    _SubEmail: CfnParameter;
    _OpenSearchIndex: CfnParameter;
    _OpenSearchIndexDict: CfnParameter;

    constructor(scope: Construct, props: CdkProps) {

        this._S3ModelAssets = new CfnParameter(scope, 'S3ModelAssets', {
            type: 'String',
            description: 'S3 Bucket for model & code assets',
            default: `ChatBot-S3ModelAsset-${props.env.stage}-${props.env.region}`
        });

        this._SubEmail = new CfnParameter(scope, 'SubEmail', {
            type: 'String',
            description: 'Email address for SNS notification',
            default: 'default@default.com'
        });

        this._OpenSearchIndex = new CfnParameter(scope, 'OpenSearchIndex', {
            type: 'String',
            description: 'OpenSearch index to store knowledge',
            default: 'chatbot-index',
        });

        let OpenSearchIndexDictDefaultValue: string | undefined;

        if (process.env.AOSDictValue !== undefined) {
            OpenSearchIndexDictDefaultValue = process.env.AOSDictValue
        } else {
            OpenSearchIndexDictDefaultValue = '{"aos_index_mkt_qd":"aws-cn-mkt-knowledge","aos_index_mkt_qq":"gcr-mkt-qq","aos_index_dgr_qd":"ug-index-20240108","aos_index_dgr_qq":"gcr-dgr-qq", "aos_index_dgr_faq_qd":"faq-index-20240110", "dummpy_key":"dummpy_value"}';
        }

        this._OpenSearchIndexDict = new CfnParameter(scope, 'OpenSearchIndexDict', {
            type: 'String',
            description: 'OpenSearch index to store knowledge dict format',
            default: OpenSearchIndexDictDefaultValue,
        });
    }
}