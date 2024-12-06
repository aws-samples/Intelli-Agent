from aikits_utils import lambda_return
from main import process_pdf_pipeline
from gevent import pywsgi
import flask
import json

app = flask.Flask(__name__)


def handler(event, context):
    if 'body' not in event:
        return lambda_return(400, 'invalid param')
    try:
        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']

        if 's3_bucket' not in body or 'object_key' not in body:
            return lambda_return(400, 'Must specify the `s3_bucket` and `object_key` for the file')

    except:
        return lambda_return(400, 'invalid param')

    output = process_pdf_pipeline(body)

    return lambda_return(200, json.dumps(output))


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
        req = handler({'body': body}, None)
        return flask.Response(
            response=req['body'],
            status=req['statusCode'], mimetype='application/json')
    else:
        return flask.Response(
            response='Only supports application/json data',
            status=415, mimetype='application/json')


server = pywsgi.WSGIServer(('0.0.0.0', 8080), app)
server.serve_forever()
