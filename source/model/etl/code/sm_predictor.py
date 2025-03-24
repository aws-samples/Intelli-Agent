from main import process_pdf_pipeline
from gevent import pywsgi
import flask
import json

app = flask.Flask(__name__)


def handler(event, context):
    if 'body' not in event:
        return create_response('invalid param', 400)
    try:
        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']

        if 's3_bucket' not in body or 'object_key' not in body:
            return create_response('Must specify the `s3_bucket` and `object_key` for the file', 400)

    except:
        return create_response('invalid param', 400)

    output = process_pdf_pipeline(body)
    return create_response(json.dumps(output), 200)


def create_response(body, status_code=200):
    """Create a Flask response with CORS headers.
    
    Args:
        body: Response body
        status_code: HTTP status code (default: 200)
        
    Returns:
        Flask Response object
    """
    response = flask.make_response(body, status_code)
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response


@app.route('/ping', methods=['GET'])
def ping():
    """
    Determine if the container is working and healthy. In this sample container, we declare
    it healthy if we can load the model successfully.
    :return:
    """
    status = 200
    return flask.Response(response='Flask app is activated.', status=status, mimetype='application/json')


@app.route('/invocations', methods=['POST'])
def transformation():
    """
    Do an inference on a single batch of data. In this sample server, we take image data as base64 formation,
    decode it for internal use and then convert the predictions to json format
    :return:
    """
    if flask.request.content_type == 'application/json':
        request_body = flask.request.data.decode('utf-8')
        body = json.loads(request_body)
        response = handler({'body': body}, None)
        return response
    else:
        return create_response('Only supports application/json data', 415)


server = pywsgi.WSGIServer(('0.0.0.0', 8080), app)
server.serve_forever()
