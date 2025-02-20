import { Aws, StackProps, RemovalPolicy } from 'aws-cdk-lib';
import {
  AccountRecovery,
  AdvancedSecurityMode,
  CfnUserPoolGroup,
  CfnUserPoolUser,
  CfnUserPoolUserToGroupAttachment,
  OAuthScope,
  UserPool,
  UserPoolDomain,
  VerificationEmailStyle,
} from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';
import { Constants } from '../shared/constants';

export interface UserProps extends StackProps {
  readonly adminEmail: string;
  readonly callbackUrls: string[];
  readonly logoutUrls: string[];
  readonly userPoolName?: string;
  readonly domainPrefix?: string;
}

export interface UserConstructOutputs {
  oidcIssuer: string;
  oidcClientId: string;
  oidcLogoutUrl: string;
  userPool: UserPool;
}

export class UserConstruct extends Construct implements UserConstructOutputs {
  public readonly oidcIssuer: string;
  public readonly oidcClientId: string;
  public readonly oidcLogoutUrl: string;
  public readonly userPool: UserPool;

  constructor(scope: Construct, id: string, props: UserProps) {
    super(scope, id);

    const userPoolName = props.userPoolName || `${Constants.SOLUTION_NAME}_UserPool`
    const domainPrefix = props.domainPrefix || `${Constants.SOLUTION_NAME.toLowerCase()}-${Aws.ACCOUNT_ID}`

    this.userPool = new UserPool(this, 'UserPool', {
      userPoolName: userPoolName,
      selfSignUpEnabled: false,
      signInCaseSensitive: false,
      accountRecovery: AccountRecovery.EMAIL_ONLY,
      removalPolicy: RemovalPolicy.DESTROY,
      signInAliases: {
        email: true,
      },
      userVerification: {
        emailStyle: VerificationEmailStyle.LINK,
      },
      advancedSecurityMode: AdvancedSecurityMode.ENFORCED,
      passwordPolicy: {
        minLength: 8,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      userInvitation: {
        emailSubject: 'Welcome to use AI Customer Service',
        emailBody: 'Hello {username}, your temporary password is {####}',
      },
    });

    // Create an unique cognito domain
    const userPoolDomain = new UserPoolDomain(this, 'UserPoolDomain', {
      userPool: this.userPool,
      cognitoDomain: {
        domainPrefix: domainPrefix,
      },
    });

    // Add UserPoolClient
    const userPoolClient = this.userPool.addClient('UserPoolClient', {
      userPoolClientName: Constants.SOLUTION_NAME,
      authFlows: {
        userSrp: true,
        userPassword: true,
      },
      oAuth: {
        callbackUrls: props.callbackUrls,
        logoutUrls: props.logoutUrls,
        scopes: [OAuthScope.OPENID, OAuthScope.PROFILE, OAuthScope.EMAIL],
      },
    });

    // Add AdminUser
    const email = props.adminEmail;
    const adminUser = new CfnUserPoolUser(this, 'AdminUser', {
      userPoolId: this.userPool.userPoolId,
      username: email,
      userAttributes: [
        {
          name: 'email',
          value: email,
        },
        {
          name: 'email_verified',
          value: 'true',
        },
      ],
    });

    // Add AdminGroup
    const adminGroup = new CfnUserPoolGroup(this, 'AdminGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'Admin',
      description: 'Admin group',
    });

    const grpupAttachment = new CfnUserPoolUserToGroupAttachment(this, 'UserGroupAttachment', {
      userPoolId: this.userPool.userPoolId,
      groupName: adminGroup.groupName!,
      username: adminUser.username!,
    });
    grpupAttachment.addDependency(adminUser);
    grpupAttachment.addDependency(adminGroup);


    this.oidcIssuer = `https://cognito-idp.${Aws.REGION}.amazonaws.com/${this.userPool.userPoolId}`;
    this.oidcClientId = userPoolClient.userPoolClientId;
    this.oidcLogoutUrl = `${userPoolDomain.baseUrl()}/logout`;
  }
}
