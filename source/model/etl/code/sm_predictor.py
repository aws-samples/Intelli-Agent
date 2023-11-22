from gevent import pywsgi
import flask
import json

import file_analyzer_app

app = flask.Flask(__name__)

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
        req = file_analyzer_app.handler({'body':body}, None)
        return flask.Response(
            response=req['body'],
            status=req['statusCode'], mimetype='application/json')
    else:
        return flask.Response(
            response='Only supports application/json data',
            status=415, mimetype='application/json')
            
server = pywsgi.WSGIServer(('0.0.0.0', 8080), app)
server.serve_forever()