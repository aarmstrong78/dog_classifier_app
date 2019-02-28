# MAKE SURE THIS FILE IS IN .gitignore so that it isn't saved on github repository
# Define settings used in the flask app
app_settings = {
        'PROJECT_ID' : 'Spotdog',
        'ALLOWED_EXTENSIONS' : set(['png', 'jpg', 'jpeg', 'gif']),
        'CLOUD_STORAGE_BUCKET' : 'spotdog.appspot.com',
        'MYSQL_HOST' : 'mysql',
        'MYSQL_PORT' : 3306,
        'MYSQL_USER' : 'dog_classifier_app',
        'MYSQL_PASSWORD' : 'asd776GHuihsdf!$',
        'MYSQL_DB' : 'dog_classifier_app',
        'MYSQL_CURSORCLASS' : 'DictCursor',
        'IMAGE_FILES_LOCATION' : '/var/data',
        'secret_key' : '45gdh56562wgyy72487987987987978'
        }
