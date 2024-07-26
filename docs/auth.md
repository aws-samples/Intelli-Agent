## Authorization

The solution is authorized by Amazon Cognito, follow below steps to invoke APIs.

### Get JWT token

Execute this command to get all the tokens, you need to replace region, client id, user name and password.

```bash
aws cognito-idp initiate-auth --region <your_region> --auth-flow USER_PASSWORD_AUTH --client-id <your_client_id> --auth-parameters USERNAME=<your_username>,PASSWORD=<your_password>
```

Example:

```bash
aws cognito-idp initiate-auth --region us-west-2 --auth-flow USER_PASSWORD_AUTH --client-id 2lvce6luqthanm4vu0jiamesc1 --auth-parameters USERNAME=foo@example.com,PASSWORD=Example123!
```

The client id can be found in Cognito console

1. Go to Cognito console and select your user pool
2. Click App integration tab and scroll down to the bottom, you will see client id in the bottom

The response is as below shown, you can see there are three types of token, you need to use **IdToken** to invoke APIs.

```bash
{
    "ChallengeParameters": {},
    "AuthenticationResult": {
        "AccessToken": "eyJraWQi",
        "ExpiresIn": 3600,
        "TokenType": "Bearer",
        "RefreshToken": "eyJjdHkiOiJ...",
        "IdToken": "eyJraWQiOiIrNE93..."
    }
}
```

## Invoke API with JWT token

### Restful API

Use HTTP client or WebSocket client to invoke APIs with JWT token as authorization header. Take Postman as an example
Note: the value should be in this format, Bearer <JWT token>, don’t forget to add Bearer

Headers example:

```bash
{
    "Authorization": "Bearer eyJraWQiOiIrNE93..."
}

```

