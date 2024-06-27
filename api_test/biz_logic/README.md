# Generating a Client with OpenAPI Generator

### Installing OpenAPI Generator

If you haven't installed OpenAPI Generator yet, you can install it using npm (Node.js required) or Homebrew (on macOS):

To install with npm:
```shell
npm install @openapitools/openapi-generator-cli -g
```

To install with Homebrew:
```shell
brew install openapi-generator
```

### Generating the Client
Use the following command to generate the client code. Assuming your OpenAPI specification file is named openapi.json and you want to generate a Python client:

```shell
openapi-generator-cli generate -i openapi.json -g python -o ./generated-client
```
In this command:

* -i openapi.json specifies the input file.
* -g python specifies the client language to generate, in this case, Python.
* -o ./generated-client specifies the output directory.

其他常见语言的选项包括：

### Viewing the Generated Client
Once the generation is complete, you can find the generated client code in the specified output directory (e.g., ./generated-client).