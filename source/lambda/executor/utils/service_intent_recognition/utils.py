import os 
import re

SERVICE_NAME_PATH = os.path.join(
    os.path.dirname(__file__),
    'service_names.txt'
)

SERVICE_NAMES = None 
SERVICE_NAMES_UPPER = None  

def get_all_service_names():
    global SERVICE_NAMES
    if SERVICE_NAMES is not None:
        return SERVICE_NAMES
    with open(SERVICE_NAME_PATH) as f:
        service_names = [s.strip() for s in f.readlines()]
    SERVICE_NAMES = service_names
    return service_names

def get_all_service_names_upper():
    global SERVICE_NAMES_UPPER
    if SERVICE_NAMES_UPPER is not None:
        return SERVICE_NAMES_UPPER 
    service_names = get_all_service_names() 
    SERVICE_NAMES_UPPER = {}
    for s in service_names:
        s_u = s.upper()
        s_r_amazon = s_u.replace("AMAZON","").strip()
        s_r_aws = s_u.replace("AWS","").strip()
        SERVICE_NAMES_UPPER.update({
            s_u:s,
            s_r_amazon:s,
            s_r_aws:s
        })
    return SERVICE_NAMES_UPPER


def exact_match(query):
    """
    exact match the service name, about 1/3 questions will be hit.
    if exact match fail, return None.
    Args:
        query (_type_): _description_

    Returns:
        _type_: _description_
    """
    service_names_upper = get_all_service_names_upper()
    # query_upper = query.upper()
    # ret = []
    # for service_name_upper in service_names_upper:
    #     if service_name_upper in query_upper:
    #         ret.append(service_names_upper[service_name_upper])
    #
    # return list(set(ret))

    matches = []
    # extract all the alphabet characters and number from the query with proper blank space
    query = re.sub(r'[^a-zA-Z0-9\s]', '', query)
    # remove aws and amazon from the query consider the lower & upper case
    query = re.sub(r'aws|amazon', '', query, flags=re.IGNORECASE)

    # use regex to iterate through the service dictionary to find the full match with each word but partial match with whole string in the query and append to the matches list
    for word in query.split():
        for key in service_names_upper.keys():
            if re.search(r'\b' + re.escape(word) + r'\b', key, flags=re.IGNORECASE):
                if service_names_upper[key] not in matches:
                    matches.append(service_names_upper[key])
    return matches

def match_service_using_knn(query):
    pass 

    
def get_service_name(query):

    exact_match_res = exact_match(query)

    return exact_match_res
    

