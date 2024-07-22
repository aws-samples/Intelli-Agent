# openapi_client.DefaultApi

All URIs are relative to *https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod*

Method | HTTP request | Description
------------- | ------------- | -------------
[**aos_get**](DefaultApi.md#aos_get) | **GET** /aos | 
[**aos_options**](DefaultApi.md#aos_options) | **OPTIONS** /aos | 
[**aos_post**](DefaultApi.md#aos_post) | **POST** /aos | 
[**batch_options**](DefaultApi.md#batch_options) | **OPTIONS** /batch | 
[**batch_post**](DefaultApi.md#batch_post) | **POST** /batch | 
[**ddb_list_messages_get**](DefaultApi.md#ddb_list_messages_get) | **GET** /ddb/list-messages | 
[**ddb_list_messages_options**](DefaultApi.md#ddb_list_messages_options) | **OPTIONS** /ddb/list-messages | 
[**ddb_list_sessions_get**](DefaultApi.md#ddb_list_sessions_get) | **GET** /ddb/list-sessions | 
[**ddb_list_sessions_options**](DefaultApi.md#ddb_list_sessions_options) | **OPTIONS** /ddb/list-sessions | 
[**ddb_options**](DefaultApi.md#ddb_options) | **OPTIONS** /ddb | 
[**ddb_post**](DefaultApi.md#ddb_post) | **POST** /ddb | 
[**etl_delete_execution_options**](DefaultApi.md#etl_delete_execution_options) | **OPTIONS** /etl/delete-execution | 
[**etl_delete_execution_post**](DefaultApi.md#etl_delete_execution_post) | **POST** /etl/delete-execution | 
[**etl_execution_get**](DefaultApi.md#etl_execution_get) | **GET** /etl/execution | 
[**etl_execution_options**](DefaultApi.md#etl_execution_options) | **OPTIONS** /etl/execution | 
[**etl_list_execution_get**](DefaultApi.md#etl_list_execution_get) | **GET** /etl/list-execution | 
[**etl_list_execution_options**](DefaultApi.md#etl_list_execution_options) | **OPTIONS** /etl/list-execution | 
[**etl_list_workspace_get**](DefaultApi.md#etl_list_workspace_get) | **GET** /etl/list-workspace | 
[**etl_list_workspace_options**](DefaultApi.md#etl_list_workspace_options) | **OPTIONS** /etl/list-workspace | 
[**etl_options**](DefaultApi.md#etl_options) | **OPTIONS** /etl | 
[**etl_post**](DefaultApi.md#etl_post) | **POST** /etl | 
[**etl_upload_s3_url_options**](DefaultApi.md#etl_upload_s3_url_options) | **OPTIONS** /etl/upload-s3-url | 
[**etl_upload_s3_url_post**](DefaultApi.md#etl_upload_s3_url_post) | **POST** /etl/upload-s3-url | 
[**extract_options**](DefaultApi.md#extract_options) | **OPTIONS** /extract | 
[**extract_post**](DefaultApi.md#extract_post) | **POST** /extract | 
[**llm_options**](DefaultApi.md#llm_options) | **OPTIONS** /llm | 
[**llm_post**](DefaultApi.md#llm_post) | **POST** /llm | 
[**prompt_management_models_get**](DefaultApi.md#prompt_management_models_get) | **GET** /prompt-management/models | 
[**prompt_management_models_options**](DefaultApi.md#prompt_management_models_options) | **OPTIONS** /prompt-management/models | 
[**prompt_management_options**](DefaultApi.md#prompt_management_options) | **OPTIONS** /prompt-management | 
[**prompt_management_prompts_get**](DefaultApi.md#prompt_management_prompts_get) | **GET** /prompt-management/prompts | 
[**prompt_management_prompts_options**](DefaultApi.md#prompt_management_prompts_options) | **OPTIONS** /prompt-management/prompts | 
[**prompt_management_prompts_post**](DefaultApi.md#prompt_management_prompts_post) | **POST** /prompt-management/prompts | 
[**prompt_management_scenes_get**](DefaultApi.md#prompt_management_scenes_get) | **GET** /prompt-management/scenes | 
[**prompt_management_scenes_options**](DefaultApi.md#prompt_management_scenes_options) | **OPTIONS** /prompt-management/scenes | 
[**root_options**](DefaultApi.md#root_options) | **OPTIONS** / | 


# **aos_get**
> object aos_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.aos_get()
        print("The response of DefaultApi->aos_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->aos_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **aos_options**
> aos_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.aos_options()
    except Exception as e:
        print("Exception when calling DefaultApi->aos_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **aos_post**
> object aos_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.aos_post()
        print("The response of DefaultApi->aos_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->aos_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **batch_options**
> batch_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.batch_options()
    except Exception as e:
        print("Exception when calling DefaultApi->batch_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **batch_post**
> object batch_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.batch_post()
        print("The response of DefaultApi->batch_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->batch_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **ddb_list_messages_get**
> object ddb_list_messages_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.ddb_list_messages_get()
        print("The response of DefaultApi->ddb_list_messages_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->ddb_list_messages_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **ddb_list_messages_options**
> ddb_list_messages_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.ddb_list_messages_options()
    except Exception as e:
        print("Exception when calling DefaultApi->ddb_list_messages_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **ddb_list_sessions_get**
> object ddb_list_sessions_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.ddb_list_sessions_get()
        print("The response of DefaultApi->ddb_list_sessions_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->ddb_list_sessions_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **ddb_list_sessions_options**
> ddb_list_sessions_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.ddb_list_sessions_options()
    except Exception as e:
        print("Exception when calling DefaultApi->ddb_list_sessions_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **ddb_options**
> ddb_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.ddb_options()
    except Exception as e:
        print("Exception when calling DefaultApi->ddb_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **ddb_post**
> object ddb_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.ddb_post()
        print("The response of DefaultApi->ddb_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->ddb_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_delete_execution_options**
> etl_delete_execution_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.etl_delete_execution_options()
    except Exception as e:
        print("Exception when calling DefaultApi->etl_delete_execution_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_delete_execution_post**
> IntellapicoFZ7zCcvP9bso etl_delete_execution_post(intellapico_pmqf0_z8_hxy1a)



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.models.intellapico_fz7z_ccv_p9bso import IntellapicoFZ7zCcvP9bso
from openapi_client.models.intellapico_pmqf0_z8_hxy1a import IntellapicoPMQf0Z8Hxy1a
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
    intellapico_pmqf0_z8_hxy1a = openapi_client.IntellapicoPMQf0Z8Hxy1a() # IntellapicoPMQf0Z8Hxy1a | 

    try:
        api_response = api_instance.etl_delete_execution_post(intellapico_pmqf0_z8_hxy1a)
        print("The response of DefaultApi->etl_delete_execution_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->etl_delete_execution_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **intellapico_pmqf0_z8_hxy1a** | [**IntellapicoPMQf0Z8Hxy1a**](IntellapicoPMQf0Z8Hxy1a.md)|  | 

### Return type

[**IntellapicoFZ7zCcvP9bso**](IntellapicoFZ7zCcvP9bso.md)

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_execution_get**
> IntellapicoDgm6W6BGKCeI etl_execution_get(execution_id=execution_id)



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.models.intellapico_dgm6_w6_bgkce_i import IntellapicoDgm6W6BGKCeI
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
    execution_id = 'execution_id_example' # str |  (optional)

    try:
        api_response = api_instance.etl_execution_get(execution_id=execution_id)
        print("The response of DefaultApi->etl_execution_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->etl_execution_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **execution_id** | **str**|  | [optional] 

### Return type

[**IntellapicoDgm6W6BGKCeI**](IntellapicoDgm6W6BGKCeI.md)

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_execution_options**
> etl_execution_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.etl_execution_options()
    except Exception as e:
        print("Exception when calling DefaultApi->etl_execution_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_list_execution_get**
> IntellapicoJOxFkqJZEOJU etl_list_execution_get(page_size=page_size, max_items=max_items)



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.models.intellapico_jox_fkq_jzeoju import IntellapicoJOxFkqJZEOJU
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
    page_size = 'page_size_example' # str |  (optional)
    max_items = 'max_items_example' # str |  (optional)

    try:
        api_response = api_instance.etl_list_execution_get(page_size=page_size, max_items=max_items)
        print("The response of DefaultApi->etl_list_execution_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->etl_list_execution_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **page_size** | **str**|  | [optional] 
 **max_items** | **str**|  | [optional] 

### Return type

[**IntellapicoJOxFkqJZEOJU**](IntellapicoJOxFkqJZEOJU.md)

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_list_execution_options**
> etl_list_execution_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.etl_list_execution_options()
    except Exception as e:
        print("Exception when calling DefaultApi->etl_list_execution_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_list_workspace_get**
> object etl_list_workspace_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.etl_list_workspace_get()
        print("The response of DefaultApi->etl_list_workspace_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->etl_list_workspace_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_list_workspace_options**
> etl_list_workspace_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.etl_list_workspace_options()
    except Exception as e:
        print("Exception when calling DefaultApi->etl_list_workspace_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_options**
> etl_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.etl_options()
    except Exception as e:
        print("Exception when calling DefaultApi->etl_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_post**
> object etl_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.etl_post()
        print("The response of DefaultApi->etl_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->etl_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_upload_s3_url_options**
> etl_upload_s3_url_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.etl_upload_s3_url_options()
    except Exception as e:
        print("Exception when calling DefaultApi->etl_upload_s3_url_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **etl_upload_s3_url_post**
> IntellapicoxS0zr8unBkag etl_upload_s3_url_post(intellapicog_aql_ungs_xxvb)



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.models.intellapicog_aql_ungs_xxvb import IntellapicogAQLUngsXXVB
from openapi_client.models.intellapicox_s0zr8un_bkag import IntellapicoxS0zr8unBkag
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
    intellapicog_aql_ungs_xxvb = openapi_client.IntellapicogAQLUngsXXVB() # IntellapicogAQLUngsXXVB | 

    try:
        api_response = api_instance.etl_upload_s3_url_post(intellapicog_aql_ungs_xxvb)
        print("The response of DefaultApi->etl_upload_s3_url_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->etl_upload_s3_url_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **intellapicog_aql_ungs_xxvb** | [**IntellapicogAQLUngsXXVB**](IntellapicogAQLUngsXXVB.md)|  | 

### Return type

[**IntellapicoxS0zr8unBkag**](IntellapicoxS0zr8unBkag.md)

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **extract_options**
> extract_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.extract_options()
    except Exception as e:
        print("Exception when calling DefaultApi->extract_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **extract_post**
> object extract_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.extract_post()
        print("The response of DefaultApi->extract_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->extract_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **llm_options**
> llm_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.llm_options()
    except Exception as e:
        print("Exception when calling DefaultApi->llm_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **llm_post**
> object llm_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.llm_post()
        print("The response of DefaultApi->llm_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->llm_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **prompt_management_models_get**
> object prompt_management_models_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.prompt_management_models_get()
        print("The response of DefaultApi->prompt_management_models_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->prompt_management_models_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **prompt_management_models_options**
> prompt_management_models_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.prompt_management_models_options()
    except Exception as e:
        print("Exception when calling DefaultApi->prompt_management_models_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **prompt_management_options**
> prompt_management_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.prompt_management_options()
    except Exception as e:
        print("Exception when calling DefaultApi->prompt_management_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **prompt_management_prompts_get**
> object prompt_management_prompts_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.prompt_management_prompts_get()
        print("The response of DefaultApi->prompt_management_prompts_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->prompt_management_prompts_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **prompt_management_prompts_options**
> prompt_management_prompts_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.prompt_management_prompts_options()
    except Exception as e:
        print("Exception when calling DefaultApi->prompt_management_prompts_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **prompt_management_prompts_post**
> object prompt_management_prompts_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.prompt_management_prompts_post()
        print("The response of DefaultApi->prompt_management_prompts_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->prompt_management_prompts_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **prompt_management_scenes_get**
> object prompt_management_scenes_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.prompt_management_scenes_get()
        print("The response of DefaultApi->prompt_management_scenes_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->prompt_management_scenes_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

[intelliagentapiconstructApiAuthorizerFB94A0DF](../README.md#intelliagentapiconstructApiAuthorizerFB94A0DF)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**400** | 400 response |  -  |
**500** | 500 response |  -  |
**200** | 200 response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **prompt_management_scenes_options**
> prompt_management_scenes_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.prompt_management_scenes_options()
    except Exception as e:
        print("Exception when calling DefaultApi->prompt_management_scenes_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **root_options**
> root_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://ycnhr2duua.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.root_options()
    except Exception as e:
        print("Exception when calling DefaultApi->root_options: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | 204 response |  * Access-Control-Allow-Origin -  <br>  * Access-Control-Allow-Methods -  <br>  * Access-Control-Allow-Credentials -  <br>  * Access-Control-Allow-Headers -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

