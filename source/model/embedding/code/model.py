from djl_python import Input, Output
import torch
import logging
from transformers import  AutoTokenizer, AutoModel

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(f'--device={device}')


def load_model(properties):
    tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties['model_dir']
    if "model_id" in properties:
        model_location = properties['model_id']
    logging.info(f"Loading model in {model_location}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_location, trust_remote_code=True)
    tokenizer.padding_side = 'right'
    model = AutoModel.from_pretrained(
        model_location, 
        # device_map="balanced_low_0", 
        trust_remote_code=True
    ).half()
    # load the model on GPU
    model.to(device) 
    model.requires_grad_(False)
    model.eval()
    
    return model, tokenizer


model = None
tokenizer = None
generator = None

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0].to(device) #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float().to(device)
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def handle(inputs: Input):
    global model, tokenizer
    if not model:
        model, tokenizer = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    input_sentences = data["inputs"]
    logging.info(f"inputs: {input_sentences}")
    
    encoded_input = tokenizer(input_sentences, padding=True, truncation=True, max_length=512, return_tensors='pt').to(device)
    # Compute token embeddings
    with torch.no_grad():
        model_output = model(**encoded_input)
        sentence_embeddings = model_output[0][:, 0]

    # Perform pooling. In this case, max pooling.
    # sentence_embeddings = model_output.cpu().numpy()
    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1).cpu().numpy()

#     # preprocess
#     input_ids = tokenizer(input_sentences, return_tensors="pt").input_ids
#     # pass inputs with all kwargs in data
#     if params is not None:
#         outputs = model.generate(input_ids, **params)
#     else:
#         outputs = model.generate(input_ids)

#     # postprocess the prediction
#     prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    result = {"sentence_embeddings": sentence_embeddings}
    return Output().add_as_json(result)