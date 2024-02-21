## AOS API Invocation Guide

This guide will walk you through the process of invoking the API.

### AOS API List

The AOS API provides the following operations:

- [Query AOS Embedding](#query-aos-embedding)
- [Delete AOS Embedding](#delete-aos-embedding)
- [Create AOS Index](#create-aos-index)
- [Inject Document Directly to AOS Index](#inject-document-directly-to-aos-index)
- [Query Embedding by Specific Field](#query-embedding-by-specific-field)
- [Query AOS Embedding by KNN Vector](#query-aos-embedding-by-knn-vector)
- [Query AOS Index for Mapping Configuration](#query-aos-index-for-mapping-configuration)


#### Query AOS Embedding

To query the AOS embedding, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos`. The request body should contain the query string and the AOS index name.

Here is an example of the request body:

```bash
{
   "aos_index": "<Your OpenSearch index>", // e.g., "dev"
   "operation": "query_all",
   "body": {}
}
```

After making the request, you should see a response similar to this:
```bash
{
   "took":4,
   "timed_out":false,
   "_shards":{
      "total":4,
      "successful":4,
      "skipped":0,
      "failed":0
   },
   "hits":{
      "total":{
         "value":256,
         "relation":"eq"
      },
      "max_score":1.0,
      "hits":[
         {
            "_index":"chatbot-index",
            "_id":"035e8439-c683-4278-97f3-151f8cd4cdb6",
            "_score":1.0,
            "_source":{
               "vector_field":[
                  -0.03106689453125,
                  -0.00798797607421875
               ],
               "text":"## 1 Introduction\n\nDeep generative models of all kinds have recently exhibited high quality samples in a wide variety of data modalities. Generative adversarial networks (GANs), autoregressive models, flows, and variational autoencoders (VAEs) have synthesized striking image and audio samples [14; 27; 3; 58; 38; 25; 10; 32; 44; 57; 26; 33; 45], and there have been remarkable advances in energy-based modeling and score matching that have produced images comparable to those of GANs [11; 55].",
               "metadata":{
                  "content_type":"paragraph",
                  "heading_hierarchy":{
                     "1 Introduction":{
                        
                     }
                  },
                  "figure_list":[
                     
                  ],
                  "chunk_id":"$2",
                  "file_path":"Denoising Diffusion Probabilistic Models.pdf",
                  "keywords":[
                     
                  ],
                  "summary":""
               }
            }
         }
      ]
   }
}
```


#### Delete AOS Embedding

To delete the AOS embedding, make a DELETE request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos`. The request body should contain the AOS index name and the document id.

Here is an example of the request body:

```bash
{
   "aos_index": "<Your OpenSearch index>", // e.g., "dev"
   "operation": "delete",
   "body": {}
}
```

After making the request, you should see a response similar to this:
```bash
{
  "acknowledged": true
}
```

#### Create AOS Index

To create an AOS index, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos`. The request body should contain the AOS index name and the index mapping.


Here is an example of the request body:

```bash
{
   "aos_index": "<Your OpenSearch index>", // e.g., "dev"
   "operation": "create_index",
   "body": {}
}
```

After making the request, you should see a response similar to this:
```bash
{
   "acknowledged": true,
   "shards_acknowledged": true,
   "index": "dev"
}
```


#### Inject Document Directly to AOS Index

To inject a document directly to the AOS index, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos`. The request body should contain the AOS index name, the document id, and the document body.


Here is an example of the request body:

```bash
{
   "aos_index":"llm-bot-index",
   "operation":"embed_document",
   "body":{
      "documents":{
         "page_content":"## Main Title\n This is the main titlebe before such chapter",
         "metadata":{
            "content_type":"paragraph",
            "heading_hierarchy":"{'Evaluation of LLM Retrievers': {}}",
            "figure_list":[
               
            ],
            "chunk_id":"$9",
            "file_path":"s3://bucket/file_folder/ec2/user_guide",
            "keywords":[
               "ec2",
               "s3"
            ],
            "summary":"This is summary for such user guide"
         }
      }
   }
}
```


After making the request, you should see a response similar to this:
```bash
{
   "statusCode":200,
   "headers":{
      "Content-Type":"application/json"
   },
   "body":{
      "document_id":[
         "1e70e167-53b4-42d1-9bdb-084c2f2d3282"
      ]
   }
}
```


#### Query Embedding by Specific Field

To query the embedding by a specific field, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos`. The request body should contain the AOS index name, the field name, and the field value.


Here is an example of the request body:

```bash
{
   "aos_index":"llm-bot-index-01",
   "operation":"query_full_text_match",
   "body":{
      "field":"metadata.file_path",
      "value":"s3://bucket/file_folder/ec2/user_guide",
      "size":100
   }
}
```

After making the request, you should see a response similar to this. The metadata.file_path field is matched with the value "s3://bucket/file_folder/ec2/user_guide" and embedding vector is returned with score for relevance possibility::
```bash
{
   "took":4,
   "timed_out":false,
   "_shards":{
      "total":5,
      "successful":5,
      "skipped":0,
      "failed":0
   },
   "hits":{
      "total":{
         "value":1,
         "relation":"eq"
      },
      "max_score":1.4384104,
      "hits":[
         {
            "_index":"llm-bot-index-01",
            "_id":"94d05a5c-1311-4c16-8f32-67b03526b888",
            "_score":1.4384104,
            "_source":{
               "vector_field":[
                  0.014800798147916794,
                  0.04196572303771973,
                  "..."
               ],
               "text":"### Evaluation of LLM Retrievers\n This is the main body of such chapter",
               "metadata":{
                  "content_type":"paragraph",
                  "heading_hierarchy":"{'Evaluation of LLM Retrievers': {}}",
                  "figure_list":[
                     
                  ],
                  "chunk_id":"$10",
                  "file_path":"s3://bucket/file_folder/ec2/user_guide",
                  "keywords":[
                     "ec2",
                     "s3"
                  ],
                  "summary":"This is summary for such user guide"
               }
            }
         }
      ]
   }
}
```


### Query AOS Embedding by KNN Vector

To query the AOS embedding by KNN vector, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos`. The request body should contain the AOS index name, the vector field, and the number of neighbors to return.


Here is an example of the request body:

```bash
{
   "aos_index":"llm-bot-index",
   "operation":"query_knn",
   "body":{
      "query":[
         0.014800798147916794,
         0.04196572303771973,
         "..."
      ],
      "size":10
   }
}
```

After making the request, you should see a response similar to this:
```bash
{
   "took":2,
   "timed_out":false,
   "_shards":{
      "total":5,
      "successful":5,
      "skipped":0,
      "failed":0
   },
   "hits":{
      "total":{
         "value":2,
         "relation":"eq"
      },
      "max_score":1.0,
      "hits":[
         {
            "_index":"llm-bot-index",
            "_id":"f57c95cb-ec45-4ea3-8c41-d364897c84ff",
            "_score":1.0,
            "_source":{
               "vector_field":[
                  0.014800798147916794,
                  0.04196572303771973,
                  "..."
               ],
               "text":"### Evaluation of LLM Retrievers\n This is the main body of such chapter",
               "metadata":{
                  "content_type":"paragraph",
                  "heading_hierarchy":"{'Evaluation of LLM Retrievers': {}}",
                  "figure_list":[
                     
                  ],
                  "chunk_id":"$10",
                  "file_path":"s3://bucket/file_folder/ec2/user_guide",
                  "keywords":[
                     "ec2",
                     "s3"
                  ],
                  "summary":"This is summary for such user guide"
               }
            }
         },
         {
            "_index":"llm-bot-index",
            "_id":"1e70e167-53b4-42d1-9bdb-084c2f2d3282",
            "_score":0.68924075,
            "_source":{
               "vector_field":[
                  -0.02339574135839939,
                  0.03578857704997063,
                  "..."
               ],
               "text":"## Main Title\n This is the main titlebe before such chapter",
               "metadata":{
                  "content_type":"paragraph",
                  "heading_hierarchy":"{'Evaluation of LLM Retrievers': {}}",
                  "figure_list":[
                     
                  ],
                  "chunk_id":"$9",
                  "file_path":"s3://bucket/file_folder/ec2/user_guide",
                  "keywords":[
                     "ec2",
                     "s3"
                  ],
                  "summary":"This is summary for such user guide"
               }
            }
         }
      ]
   }
}
```

### Query AOS Index for Mapping Configuration

To query the AOS index for mapping configuration, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/aos`. The request body should contain the AOS index name and the operation to perform.


Here is an example of the request body:

```bash
{
   "aos_index":"llm-bot-index",
   "operation":"query_index",
   "body":{}
}
```

After making the request, you should see a response similar to this:
```bash
{
   "llm-bot-index":{
      "mappings":{
         "properties":{
            "metadata":{
               "properties":{
                  "chunk_id":{
                     "type":"text",
                     "fields":{
                        "keyword":{
                           "type":"keyword",
                           "ignore_above":256
                        }
                     }
                  },
                  "content_type":{
                     "type":"text",
                     "fields":{
                        "keyword":{
                           "type":"keyword",
                           "ignore_above":256
                        }
                     }
                  },
                  "file_path":{
                     "type":"text",
                     "fields":{
                        "keyword":{
                           "type":"keyword",
                           "ignore_above":256
                        }
                     }
                  },
                  "heading_hierarchy":{
                     "type":"text",
                     "fields":{
                        "keyword":{
                           "type":"keyword",
                           "ignore_above":256
                        }
                     }
                  },
                  "keywords":{
                     "type":"text",
                     "fields":{
                        "keyword":{
                           "type":"keyword",
                           "ignore_above":256
                        }
                     }
                  },
                  "summary":{
                     "type":"text",
                     "fields":{
                        "keyword":{
                           "type":"keyword",
                           "ignore_above":256
                        }
                     }
                  }
               }
            },
            "text":{
               "type":"text",
               "fields":{
                  "keyword":{
                     "type":"keyword",
                     "ignore_above":256
                  }
               }
            },
            "vector_field":{
               "type":"float"
            }
         }
      }
   }
}
```