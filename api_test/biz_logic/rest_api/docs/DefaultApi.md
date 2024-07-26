# openapi_client.DefaultApi

All URIs are relative to *https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod*

Method | HTTP request | Description
------------- | ------------- | -------------
[**aos_get**](DefaultApi.md#aos_get) | **GET** /aos | 
[**aos_options**](DefaultApi.md#aos_options) | **OPTIONS** /aos | 
[**aos_post**](DefaultApi.md#aos_post) | **POST** /aos | 
[**chat_history_messages_get**](DefaultApi.md#chat_history_messages_get) | **GET** /chat-history/messages | 
[**chat_history_messages_options**](DefaultApi.md#chat_history_messages_options) | **OPTIONS** /chat-history/messages | 
[**chat_history_options**](DefaultApi.md#chat_history_options) | **OPTIONS** /chat-history | 
[**chat_history_post**](DefaultApi.md#chat_history_post) | **POST** /chat-history | 
[**chat_history_sessions_get**](DefaultApi.md#chat_history_sessions_get) | **GET** /chat-history/sessions | 
[**chat_history_sessions_options**](DefaultApi.md#chat_history_sessions_options) | **OPTIONS** /chat-history/sessions | 
[**chatbot_management_chatbots_get**](DefaultApi.md#chatbot_management_chatbots_get) | **GET** /chatbot-management/chatbots | 
[**chatbot_management_chatbots_options**](DefaultApi.md#chatbot_management_chatbots_options) | **OPTIONS** /chatbot-management/chatbots | 
[**chatbot_management_chatbots_post**](DefaultApi.md#chatbot_management_chatbots_post) | **POST** /chatbot-management/chatbots | 
[**chatbot_management_options**](DefaultApi.md#chatbot_management_options) | **OPTIONS** /chatbot-management | 
[**extract_options**](DefaultApi.md#extract_options) | **OPTIONS** /extract | 
[**extract_post**](DefaultApi.md#extract_post) | **POST** /extract | 
[**knowledge_base_executions_delete**](DefaultApi.md#knowledge_base_executions_delete) | **DELETE** /knowledge-base/executions | 
[**knowledge_base_executions_execution_id_get**](DefaultApi.md#knowledge_base_executions_execution_id_get) | **GET** /knowledge-base/executions/{executionId} | 
[**knowledge_base_executions_execution_id_options**](DefaultApi.md#knowledge_base_executions_execution_id_options) | **OPTIONS** /knowledge-base/executions/{executionId} | 
[**knowledge_base_executions_get**](DefaultApi.md#knowledge_base_executions_get) | **GET** /knowledge-base/executions | 
[**knowledge_base_executions_options**](DefaultApi.md#knowledge_base_executions_options) | **OPTIONS** /knowledge-base/executions | 
[**knowledge_base_executions_post**](DefaultApi.md#knowledge_base_executions_post) | **POST** /knowledge-base/executions | 
[**knowledge_base_kb_presigned_url_options**](DefaultApi.md#knowledge_base_kb_presigned_url_options) | **OPTIONS** /knowledge-base/kb-presigned-url | 
[**knowledge_base_kb_presigned_url_post**](DefaultApi.md#knowledge_base_kb_presigned_url_post) | **POST** /knowledge-base/kb-presigned-url | 
[**knowledge_base_options**](DefaultApi.md#knowledge_base_options) | **OPTIONS** /knowledge-base | 
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# **chat_history_messages_get**
> object chat_history_messages_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.chat_history_messages_get()
        print("The response of DefaultApi->chat_history_messages_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->chat_history_messages_get: %s\n" % e)
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

# **chat_history_messages_options**
> chat_history_messages_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.chat_history_messages_options()
    except Exception as e:
        print("Exception when calling DefaultApi->chat_history_messages_options: %s\n" % e)
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

# **chat_history_options**
> chat_history_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.chat_history_options()
    except Exception as e:
        print("Exception when calling DefaultApi->chat_history_options: %s\n" % e)
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

# **chat_history_post**
> object chat_history_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.chat_history_post()
        print("The response of DefaultApi->chat_history_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->chat_history_post: %s\n" % e)
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

# **chat_history_sessions_get**
> object chat_history_sessions_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.chat_history_sessions_get()
        print("The response of DefaultApi->chat_history_sessions_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->chat_history_sessions_get: %s\n" % e)
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

# **chat_history_sessions_options**
> chat_history_sessions_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.chat_history_sessions_options()
    except Exception as e:
        print("Exception when calling DefaultApi->chat_history_sessions_options: %s\n" % e)
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

# **chatbot_management_chatbots_get**
> object chatbot_management_chatbots_get()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.chatbot_management_chatbots_get()
        print("The response of DefaultApi->chatbot_management_chatbots_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->chatbot_management_chatbots_get: %s\n" % e)
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

# **chatbot_management_chatbots_options**
> chatbot_management_chatbots_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.chatbot_management_chatbots_options()
    except Exception as e:
        print("Exception when calling DefaultApi->chatbot_management_chatbots_options: %s\n" % e)
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

# **chatbot_management_chatbots_post**
> object chatbot_management_chatbots_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.chatbot_management_chatbots_post()
        print("The response of DefaultApi->chatbot_management_chatbots_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->chatbot_management_chatbots_post: %s\n" % e)
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

# **chatbot_management_options**
> chatbot_management_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.chatbot_management_options()
    except Exception as e:
        print("Exception when calling DefaultApi->chatbot_management_options: %s\n" % e)
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

# **extract_options**
> extract_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# **knowledge_base_executions_delete**
> IntellapicooRaF6JYGkSXc knowledge_base_executions_delete(intellapicobi_goe5_lboi9l)



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.models.intellapicobi_goe5_lboi9l import IntellapicobiGoe5Lboi9l
from openapi_client.models.intellapicoo_ra_f6_jygk_sxc import IntellapicooRaF6JYGkSXc
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
    intellapicobi_goe5_lboi9l = openapi_client.IntellapicobiGoe5Lboi9l() # IntellapicobiGoe5Lboi9l | 

    try:
        api_response = api_instance.knowledge_base_executions_delete(intellapicobi_goe5_lboi9l)
        print("The response of DefaultApi->knowledge_base_executions_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_executions_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **intellapicobi_goe5_lboi9l** | [**IntellapicobiGoe5Lboi9l**](IntellapicobiGoe5Lboi9l.md)|  | 

### Return type

[**IntellapicooRaF6JYGkSXc**](IntellapicooRaF6JYGkSXc.md)

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

# **knowledge_base_executions_execution_id_get**
> IntellapicoDVrhxLpgo6Jl knowledge_base_executions_execution_id_get(execution_id)



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.models.intellapico_d_vrhx_lpgo6_jl import IntellapicoDVrhxLpgo6Jl
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
    execution_id = 'execution_id_example' # str | 

    try:
        api_response = api_instance.knowledge_base_executions_execution_id_get(execution_id)
        print("The response of DefaultApi->knowledge_base_executions_execution_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_executions_execution_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **execution_id** | **str**|  | 

### Return type

[**IntellapicoDVrhxLpgo6Jl**](IntellapicoDVrhxLpgo6Jl.md)

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

# **knowledge_base_executions_execution_id_options**
> knowledge_base_executions_execution_id_options(execution_id)



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)
    execution_id = 'execution_id_example' # str | 

    try:
        api_instance.knowledge_base_executions_execution_id_options(execution_id)
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_executions_execution_id_options: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **execution_id** | **str**|  | 

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

# **knowledge_base_executions_get**
> IntellapicollZHBI8WaBMp knowledge_base_executions_get(page_size=page_size, max_items=max_items)



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.models.intellapicoll_zhbi8_wa_bmp import IntellapicollZHBI8WaBMp
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.knowledge_base_executions_get(page_size=page_size, max_items=max_items)
        print("The response of DefaultApi->knowledge_base_executions_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_executions_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **page_size** | **str**|  | [optional] 
 **max_items** | **str**|  | [optional] 

### Return type

[**IntellapicollZHBI8WaBMp**](IntellapicollZHBI8WaBMp.md)

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

# **knowledge_base_executions_options**
> knowledge_base_executions_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.knowledge_base_executions_options()
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_executions_options: %s\n" % e)
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

# **knowledge_base_executions_post**
> object knowledge_base_executions_post()



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
        api_response = api_instance.knowledge_base_executions_post()
        print("The response of DefaultApi->knowledge_base_executions_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_executions_post: %s\n" % e)
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

# **knowledge_base_kb_presigned_url_options**
> knowledge_base_kb_presigned_url_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.knowledge_base_kb_presigned_url_options()
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_kb_presigned_url_options: %s\n" % e)
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

# **knowledge_base_kb_presigned_url_post**
> IntellapicoaPl9oPKDboEh knowledge_base_kb_presigned_url_post(intellapicop_ale5_pxt4ttp)



### Example

* Api Key Authentication (intelliagentapiconstructApiAuthorizerFB94A0DF):

```python
import openapi_client
from openapi_client.models.intellapicoa_pl9o_pk_dbo_eh import IntellapicoaPl9oPKDboEh
from openapi_client.models.intellapicop_ale5_pxt4ttp import IntellapicopALE5PXT4ttp
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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
    intellapicop_ale5_pxt4ttp = openapi_client.IntellapicopALE5PXT4ttp() # IntellapicopALE5PXT4ttp | 

    try:
        api_response = api_instance.knowledge_base_kb_presigned_url_post(intellapicop_ale5_pxt4ttp)
        print("The response of DefaultApi->knowledge_base_kb_presigned_url_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_kb_presigned_url_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **intellapicop_ale5_pxt4ttp** | [**IntellapicopALE5PXT4ttp**](IntellapicopALE5PXT4ttp.md)|  | 

### Return type

[**IntellapicoaPl9oPKDboEh**](IntellapicoaPl9oPKDboEh.md)

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

# **knowledge_base_options**
> knowledge_base_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.knowledge_base_options()
    except Exception as e:
        print("Exception when calling DefaultApi->knowledge_base_options: %s\n" % e)
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

# **llm_options**
> llm_options()



### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

# Defining the host is optional and defaults to https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "https://o9ey3xyse7.execute-api.us-east-1.amazonaws.com/prod"
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

