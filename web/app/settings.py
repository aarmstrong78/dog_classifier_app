# MAKE SURE THIS FILE IS IN .gitignore so that it isn't saved on github repository
# Define settings used in the flask app
app_settings = {
        'MYSQL_HOST' : 'mysql',
        'MYSQL_PORT' : 3306,
        'MYSQL_USER' : 'dog_classifier_app',
        'MYSQL_PASSWORD' : 'asd776GHuihsdf!$',
        'MYSQL_DB' : 'dog_classifier_app',
        'MYSQL_CURSORCLASS' : 'DictCursor',
#        'IMAGE_FILES_LOCATION' : '/tmp/ubuntu/Python/Flask/dog_classifier_app/uploads'
        'IMAGE_FILES_LOCATION' : '.'
        }