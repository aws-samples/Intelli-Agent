import { NestedStack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as dotenv from "dotenv";

dotenv.config();

interface AssetsStackProps extends StackProps {
    s3ModelAssets: string;
}

export class AssetsStack extends NestedStack {
    rerankModelPrefix;
    rerankModelVersion;
    embeddingModelPrefix;
    embeddingModelVersion;
    instructModelPrefix;
    instructModelVersion;
    etlCodePrefix;

    constructor(scope: Construct, id: string, props: AssetsStackProps) {
        super(scope, id, props);

        const rerankModelPrefix = "bge-reranker-large"
        const rerankModelVersion = "27c9168d479987529781de8474dff94d69beca11"
        const embeddingModelPrefix: string[] = ["bge-m3"]
        const embeddingModelVersion: string[] = ["3ab7155aa9b89ac532b2f2efcc3f136766b91025"]
        const instructModelPrefix = "internlm2-chat-20b"
        const instructModelVersion = "7bae8edab7cf91371e62506847f2e7fdc24c6a65"
        const etlCodePrefix = "buffer_etl_deploy_code"

        this.rerankModelPrefix = rerankModelPrefix
        this.rerankModelVersion = rerankModelVersion
        this.embeddingModelPrefix = embeddingModelPrefix
        this.embeddingModelVersion = embeddingModelVersion
        this.instructModelPrefix = instructModelPrefix
        this.instructModelVersion = instructModelVersion
        this.etlCodePrefix = etlCodePrefix
    }
}
