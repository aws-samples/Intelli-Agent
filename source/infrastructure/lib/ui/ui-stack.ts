/**********************************************************************************************************************
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                    *
 *                                                                                                                    *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import { Aws, StackProps, Stack, CfnOutput } from "aws-cdk-lib";
import { Construct } from "constructs";
import { join } from "path";

import { SystemConfig } from "../shared/types";
import { PortalConstruct } from "../ui/ui-portal";
import { UserConstruct } from "../user/user-construct";



interface UIStackProps extends StackProps {
  readonly config: SystemConfig;
}

export interface UIStackOutputs {
  readonly mainPortalConstruct: PortalConstruct;
  readonly clientPortalConstruct: PortalConstruct;
  readonly userConstruct?: UserConstruct;
}

export class UIStack extends Stack implements UIStackOutputs {

  public mainPortalConstruct: PortalConstruct;
  public clientPortalConstruct: PortalConstruct;
  public userConstruct?: UserConstruct;

  constructor(scope: Construct, id: string, props: UIStackProps) {
    super(scope, id, props);

    const mainPortalConstruct = new PortalConstruct(this, "MainUI", {
      responseHeadersPolicyName: `SecHdr${Aws.REGION}${Aws.STACK_NAME}-main`
    });
    const clientPortalConstruct = new PortalConstruct(this, "ClientUI", {
      uiSourcePath: join(__dirname, "../../../cs-portal/dist"),
      responseHeadersPolicyName: `SecHdr${Aws.REGION}${Aws.STACK_NAME}-client`
    });
    if (!props.config.deployRegion.startsWith("cn-")) {
    const userConstruct = new UserConstruct(this, "User", {
      deployRegion: props.config.deployRegion,
      adminEmail: props.config.email,
      callbackUrls: [
        `https://${clientPortalConstruct.portalUrl}/signin`,
        `https://${mainPortalConstruct.portalUrl}/signin`
      ],
      logoutUrls: [
        `https://${clientPortalConstruct.portalUrl}`,
        `https://${mainPortalConstruct.portalUrl}`
      ],
      // userPoolName: `${Constants.SOLUTION_NAME}-workspace_UserPool`,
      // domainPrefix: `${Constants.SOLUTION_NAME.toLowerCase()}-workspace-${Aws.ACCOUNT_ID}`,
    });
    this.userConstruct = userConstruct;
    // Add CfnOutputs to export values
    new CfnOutput(this, 'UserPoolId', {
      value: userConstruct.userPoolId,
      exportName: `${id}-user-pool-id`
    });

    new CfnOutput(this, 'OidcClientId', {
      value: userConstruct.oidcClientId,
      exportName: `${id}-oidc-client-id`
    });

    new CfnOutput(this, 'OidcIssuer', {
      value: userConstruct.oidcIssuer,
      exportName: `${id}-oidc-issuer`
    });

    new CfnOutput(this, 'OidcLogoutUrl', {
      value: userConstruct.oidcLogoutUrl,
      exportName: `${id}-oidc-logout-url`
    });
    new CfnOutput(this, 'OidcRegion', {
      value: userConstruct.userPoolId,
      exportName: `${id}-oidc-region`
    });
    new CfnOutput(this, 'OidcDomain', {
      value: userConstruct.userPoolId,
      exportName: `${id}-oidc-domain`
    });
    }
    this.mainPortalConstruct = mainPortalConstruct;
    this.clientPortalConstruct = clientPortalConstruct;
    

    

    new CfnOutput(this, 'PortalBucketName', {
      value: mainPortalConstruct.portalBucket.bucketName,
      exportName: `${id}-portal-bucket-name`
    });

    new CfnOutput(this, 'ClientPortalBucketName', {
      value: clientPortalConstruct.portalBucket.bucketName,
      exportName: `${id}-client-portal-bucket-name`
    });

    new CfnOutput(this, 'PortalUrl', {
      value: mainPortalConstruct.portalUrl,
      exportName: `${id}-portal-url`
    });

    new CfnOutput(this, 'ClientPortalUrl', {
      value: clientPortalConstruct.portalUrl,
      exportName: `${id}-client-portal-url`
    });
  }
}
