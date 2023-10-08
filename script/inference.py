from flask import Flask, request, jsonify

app = Flask(__name__)
# model = tf.keras.models.load_model('xx')

@app.route('/infer', methods=['GET', 'POST'])
def predict():
    data = request.json
    # Preprocess and run inference here
    # ...
    # result = model.predict(data)
    # return jsonify(result.tolist())
    print(data)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
