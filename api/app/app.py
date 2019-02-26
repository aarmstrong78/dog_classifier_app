import requests

from flask import Flask, jsonify, request
#import pandas as pd
import os
import io
#from sklearn.externals import joblib
#from sklearn.linear_model import LinearRegression
import h5py
import keras
import numpy as np
import cv2

import tensorflow as tf
from keras.backend.tensorflow_backend import set_session


from google.cloud import storage

from app.settings import *  #loads in the config settings variable

config = tf.ConfigProto(device_count = {'CPU' : 1, 'GPU' : 0})  #GPUs set to zero so we only use CPU\n",
session = tf.Session(config=config)
set_session(session)


app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = app_settings['UPLOAD_FOLDER']
app.config['CLOUD_STORAGE_BUCKET'] = app_settings['CLOUD_STORAGE_BUCKET']
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('app/spotdog-90809b2458ef.json')


#def init():
global model,graph, dog_names
# load the pre-trained Keras model
model = keras.models.load_model('app/dog_classifier.h5')
model._make_predict_function()
#h5f = h5py.File('dog_labels.h5', 'r')
#dog_names = h5f['dogs'][:]
dog_names = np.load('app/dog_labels.npy')
#h5f.close()

#def download_blob(bucket_name, source_blob_name, destination_file_name):
#    """Downloads a blob from the bucket."""
#    storage_client = storage.Client()
#    bucket = storage_client.get_bucket(bucket_name)
#    blob = bucket.blob(source_blob_name)
#
#    blob.download_to_filename(destination_file_name)
#
#    print('Blob {} downloaded to {}.'.format(
#        source_blob_name,
#        destination_file_name))


@app.route("/dog_classifier_api/predict", methods=['POST'])
def predict():
    if request.method == 'POST':
#        try:
            #data = request.get_json()
            #years_of_experience = float(data["yearsOfExperience"])

            #lin_reg = joblib.load("./linear_regression_model.pkl")
#            if not 'file' in request.files:
#                return jsonify({'error': 'no file'})  #, 400

            ###################
            # This block was used when the actual file was being sent from teh web app, rather than url to google cloud
            # Image info
            #img_file = request.files.get('file')
            #img_name = img_file.filename
            #mimetype = img_file.content_type
            ##################
            img_filename = 'image'
            app.logger.error("The post in json form:")
            app.logger.error(request.get_json())

            request_json = request.get_json()
            img_url = request_json['image_url']
            app.logger.error("The url:")
            app.logger.error(img_url)

#            download_blob(app.config['CLOUD_STORAGE_BUCKET'], img_url, img_filename)
##            r = requests.get(img_url, allow_redirects=True) # note, was using stream=True to load as binary

        	# download the image, convert it to a NumPy array, and then read
        	# it into OpenCV format
#            image = np.asarray(bytearray(r.content), dtype="uint8")
#            image = cv2.imdecode(image, cv2.IMREAD_COLOR)


##            open(img_filename, 'wb').write(r.content)
            # Return an error if not a valid mimetype
#            if not mimetype in valid_mimetypes:
#                return jsonify({'error': 'bad-type'})
            # Write image to static directory and do the hot dog check
#            img_file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_url))

            image_resize = 150
            X = []
#            img = cv2.imread(os.path.join(app.config['UPLOAD_FOLDER'], img_name))
#            img = cv2.imread(img_filename)

            img_res = requests.get(img_url)
#            app.logger.error("The Google Cloud storage response:")
#            app.logger.error(img_res.text)

            img_stream = io.BytesIO(img_res.content)
            img = cv2.imdecode(np.fromstring(img_stream.read(), np.uint8), 1)

            X.append(cv2.resize(img, (image_resize, image_resize)))
            X = np.array(X, np.float32) / 255.
            prediction = model.predict(X, verbose=0)

            # Get top n=3 predictions
            n=3
            flat_indices = np.argpartition(-prediction, n-1)[0][:n]
            breed = dog_names[flat_indices][:n].tolist()
            print(flat_indices)
            print(breed)
            #flat_indices = numpy.argpartition(prediction.ravel(), n-1)[:n]
            # for 2D array  row_indices, col_indices = numpy.unravel_index(flat_indices, prediction.shape)


#            hot_dog_conf = rekognizer.get_confidence(img_name)
            # Delete image when done with analysis
#            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img_name))
#            is_hot_dog = 'false' if hot_dog_conf == 0 else 'true'
#            return_packet = {
#                'is_hot_dog': is_hot_dog,
#                'confidence': hot_dog_conf
#            }
#            return jsonify(return_packet)
            #breed = prediction[0][0]
            #breed = 'Dog'
#            return_packet = {
#                'is_hot_dog': is_hot_dog,
#                'confidence': hot_dog_conf
#            }
#            return jsonify(return_packet)
            return_packet = {
                'dog': breed,
#                'file': img_name,
#                'type': mimetype
            }
            return jsonify(return_packet)

#        except ValueError:
#            return jsonify("Please enter a number.")


if __name__ == '__main__':
    init()
    app.run(debug=True)
