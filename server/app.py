#!/usr/bin/env python3

from flask import Flask, request
from flask_migrate import Migrate
from flask_restful import Api, Resource
from sqlalchemy import select
from marshmallow import Schema, fields, ValidationError
from werkzeug.exceptions import (
    NotFound,
    BadRequest,
    Unauthorized,
    Forbidden,
    InternalServerError,
)

from models import db, Plant

# Create a new Flask application
app = Flask(__name__)
# Configure the application to use a SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///plants.db"
# Disable SQLAlchemy's event system, which is not needed in this application
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Configure the application to use compact JSON
app.json.compact = False
# Initialize Flask-Migrate, which handles database migrations
migrate = Migrate(app, db)
# Initialize SQLAlchemy with the Flask application
db.init_app(app)
# Create a new Flask-RESTful API with the Flask application
api = Api(app)


# Define a schema for Plant objects using Marshmallow
class PlantSchema(Schema):
    id = fields.Int(
        dump_only=True
    )  # ID field, which is not required when creating a new plant
    name = fields.Str(required=True)  # Name field, which is required
    image = fields.Str(required=True)  # Image field, which is required
    price = fields.Float(required=True)  # Price field, which is required
    is_in_stock = fields.Bool(required=True)  # Is_in_stock field, which is required


# Create an instance of PlantSchema
plant_schema = PlantSchema()


# Define a decorator function for handling errors
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            # Call the decorated function and return its result
            return func(*args, **kwargs)
        except NotFound as e:
            return {"error": e.description}, 404
        except ValidationError as e:
            db.session.rollback()
            return {"message": e.messages}, 422
        except BadRequest as e:
            return {"error": e.description}, 400
        except Unauthorized as e:
            return {"error": e.description}, 401
        except Forbidden as e:
            return {"error": e.description}, 403
        except InternalServerError as e:
            return {"error": "Internal server error"}, 500
        except Exception as e:
            db.session.rollback()
            return {"message": str(e)}, 422

    return wrapper


class Plants(Resource):

    #!#!#!
    @handle_errors
    def get(self):
        # Execute a select query to get all plants
        result = db.session.execute(select(Plant))
        # Fetch all plants from the result
        plants = result.scalars().all()
        # If no plants were found, return an error message
        if not plants:
            return {"message": "Plant not found"}, 404
        # Otherwise, return the plants
        return plant_schema.dump(plants, many=True), 200

    @handle_errors
    def post(self):
        # Get the request data, which can be form data or JSON data
        data = request.get_json() if request.is_json else request.form
        # Validate and deserialize the data
        data = plant_schema.load(data)
        # Create a new plant with the data
        new_plant = Plant(**data)
        # Add the new plant to the session
        db.session.add(new_plant)
        # Commit the session to save the new plant
        db.session.commit()
        # Return the new plant
        return plant_schema.dump(new_plant), 201


api.add_resource(Plants, "/plants")


class PlantByID(Resource):

    def get_plant_by_id(self, id):
        # Execute a select query to get the plant with the given ID
        stmt = select(Plant).where(Plant.id == id)
        result = db.session.execute(stmt)
        # Fetch the first plant from the result
        plant = result.scalars().first()
        # If no plant was found, return None
        if plant is None:
            return None
        # Otherwise, return the plant
        return plant

    @handle_errors
    def get(self, id):
        # Get the plant with the given ID
        plant = self.get_plant_by_id(id)
        # If no plant was found, return an error message
        if plant is None:
            return {"message": "Plant not found"}, 404
        # Otherwise, return the plant
        return plant_schema.dump(plant), 200

    @handle_errors
    def patch(self, id):
        # Get the plant with the given ID
        plant = self.get_plant_by_id(id)
        # If no plant was found, return an error message
        if plant is None:
            return {"message": "Plant not found"}, 404
        # Get the request data, which can be form data or JSON data
        data = request.get_json() if request.is_json else request.form
        # Validate and deserialize the data
        data = plant_schema.load(data, partial=True)
        # Update the plant with the data
        for key, value in data.items():
            setattr(plant, key, value)
        # Commit the session to save the changes
        db.session.commit()
        # Return the updated plant
        return plant_schema.dump(plant), 200

    @handle_errors
    def delete(self, id):
        # Get the plant with the given ID
        plant = self.get_plant_by_id(id)
        # If no plant was found, return an error message
        if plant is None:
            return {"message": "Plant not found"}, 404
        # Delete the plant
        db.session.delete(plant)
        # Commit the session to save the changes
        db.session.commit()
        # Return no content
        return "", 204


api.add_resource(PlantByID, "/plants/<int:id>")


if __name__ == "__main__":
    app.run(port=5555, debug=True)
