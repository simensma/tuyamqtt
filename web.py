# from flask import Flask, jsonify, request, send_from_directory 
# from flask_restful import Resource, Api 
# from database import *

# app = Flask(__name__) 
# api = Api(app) 

# class Entities(Resource):

#     def get(self):

#         return jsonify(get_entities())

#     def post(self): 
          
#         data = request.get_json()     # status code 
#         return jsonify({'data': data}),

# class Settings(Resource):

#     def get(self):

#         return jsonify(get_settings())

# @app.route('/js/<path:path>')
# def send_js(path):
#     return send_from_directory('web/public/js', path)

# @app.route('/')
# def send_index():
#     return send_from_directory('web/public/html/','index.html')

# @app.route('/html/<path:path>')
# def send_html(path):
#     return send_from_directory('web/html', path)

# api.add_resource(Entities, '/api/entities') 
# api.add_resource(Settings, '/api/settings')

# app.run(debug = True) 

from flask import Flask, jsonify, request, send_from_directory 
from flask_cors import CORS, cross_origin
from flask_rest_jsonapi import Api, ResourceDetail, ResourceList, ResourceRelationship
from flask_sqlalchemy import SQLAlchemy
from marshmallow_jsonapi.flask import Schema, Relationship
from marshmallow_jsonapi import fields

# Create the Flask application and the Flask-SQLAlchemy object.
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://///home/niels/tools/tuyamqtt/config/tuyamqtt.db'
db = SQLAlchemy(app)

cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

# Create model
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    value = db.Column(db.Text)

class Entities(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deviceid = db.Column(db.Text, unique=True)
    localkey = db.Column(db.Text)
    ip  = db.Column(db.Text)
    protocol  = db.Column(db.Text)
    topic  = db.Column(db.Text)
    attributes  = db.Column(db.Text)
    status_poll = db.Column(db.Float) 
    # status_command  = db.Column(db.Integer)
    # hass_discover = db.Column(db.Boolean)
    # name  = db.Column(db.Text)

# Create the database.
db.create_all()

# Create schema
class SettingsSchema(Schema):
    class Meta:
        type_ = 'setting'
        self_view = 'setting_detail'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = 'setting_list'

    id = fields.Integer(as_string=True, dump_only=True)
    name = fields.Str()
    value = fields.Str()

class EntitiesSchema(Schema):
    class Meta:
        type_ = 'entity'
        self_view = 'entity_detail'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = 'entity_list'

    id = fields.Integer(as_string=True, dump_only=True)    
    deviceid = fields.Str()
    localkey = fields.Str()
    ip = fields.Str()
    protocol = fields.Str()
    topic = fields.Str()
    attributes = fields.Str()
    status_poll = fields.Str()
    hass_discover = fields.Str()
# Create resource managers

class SettingsList(ResourceList):
    schema = SettingsSchema
    data_layer = {'session': db.session,
                  'model': Settings}

class SettingsDetail(ResourceDetail):
    schema = SettingsSchema
    data_layer = {'session': db.session,
                  'model': Settings}

class EntitiesList(ResourceList):
    schema = EntitiesSchema
    data_layer = {'session': db.session,
                  'model': Entities}

class EntitiesDetail(ResourceDetail):
    schema = EntitiesSchema
    data_layer = {'session': db.session,
                  'model': Entities}

# Create the API object
api = Api(app)
api.route(SettingsList, 'setting_list', '/api/settings')
api.route(SettingsDetail, 'setting_detail', '/api/settings/<int:id>')
api.route(EntitiesList, 'entity_list', '/api/entities')
api.route(EntitiesDetail, 'entity_detail', '/api/entities/<int:id>')

@app.route('/')
def send_index():
    return send_from_directory('web/dist/','index.html')

@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('web/dist/css', path)

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('web/dist/js', path)

@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory('web/dist/img', path)

# Start the flask loop
if __name__ == '__main__':
    app.run()