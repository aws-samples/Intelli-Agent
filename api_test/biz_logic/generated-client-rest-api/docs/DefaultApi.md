# openapi_client.DefaultApi

All URIs are relative to *https://scw5prvr60.execute-api.us-east-1.amazonaws.com/prod*

Method | HTTP request | Description
------------- | ------------- | -------------
[**aos_post**](DefaultApi.md#aos_post) | **POST** /aos | 


# **aos_post**
> aos_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://scw5prvr60.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://scw5prvr60.execute-api.us-east-1.amazonaws.com/prod"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: intelliagentapiconstructApiAuthorizerFB94A0DF
configuration.api_key['intelliagentapiconstructApiAuthorizerFB94A0DF'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['intelliagentapiconstructApiAuthorizerFB94A0DF'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.aos_post()
    except Exception as e:
        print("Exception when calling DefaultApi->aos_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

