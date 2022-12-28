from flask import Flask, jsonify, request, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, desc,asc
from flask_marshmallow import Marshmallow
import datetime
from datetimerange import DateTimeRange
from flask_cors import CORS,cross_origin
import os


## Setting up the app
app = Flask(__name__)
CORS(app)

## Setting up SQLAlchemy
basedir = os.getcwd() ## the path for the application itself
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(os.path.join(basedir, 'booking.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

## Adding CLI Command for DB creation and deletion
@app.cli.command('db_create')
def db_create():
    db.create_all()
    print('Database created!')

@app.cli.command('db_drop')
def db_drop():
    db.drop_all()
    print('Database dropped!')

@app.cli.command('db_seed')
def db_seed():
    pass

## Creating API

## Default Route
@app.route('/')
def home():
    return jsonify(message='Booking API')

## Add Appointments
@app.route('/add_appointments', methods=['POST','OPTIONS'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
def add_appointment():
    date = request.json['date']
    time_from = request.json['time_from']
    time_to = request.json['time_to']

    if date == '' or time_from == '' or time_to == '':
        return jsonify(message='date and time cannot be blank'),406

    date_time_from = datetime.datetime.strptime(f'{date}-{time_from}','%Y-%m-%d-%H:%M')
    date_time_to = datetime.datetime.strptime(f'{date}-{time_to}','%Y-%m-%d-%H:%M')
    recieved_dates = DateTimeRange(f'{date}T{time_from}', f'{date}T{time_to}')

    ## any booking for the past dates or time cannot be accomodated.
    if datetime.datetime.now() > date_time_from:
        return jsonify(message='Any booking for the past dates or time cannot be accomodated'),406
    if date_time_from > date_time_to:
        return jsonify(message='Any booking for the past dates or time cannot be accomodated'), 406

    ## booking are'nt allowed during sunday
    if datetime.datetime.strptime(date,'%Y-%m-%d').weekday() == 6:
        return jsonify(message='Sorry appointments are only allowed from Monday to Saturday'),406

    ## bookings only allowed during opening-hourse
    opening_hours = DateTimeRange(f'{date}T09:00', f'{date}T17:00')
    if (recieved_dates in opening_hours) == False:
        return jsonify(message='Appointments are only allowed from 9:00AM - 5:00PM'),406

    ## check for conflicting booking records
    success_message = 'You added a new record!'
    datas = Appointment.query.all()
    if datas:
        for data in datas:
            data_dates = DateTimeRange(str(data.date_time_from).replace(' ','T'),str(data.date_time_to).replace(' ','T'))
            if data_dates.is_intersection(recieved_dates):
                return jsonify(message='There is a conflict between your schedule'),409

    ## adding records to the database
    first_name = request.json['first_name']
    last_name = request.json['last_name']
    title = request.json['title']
    print(first_name, last_name, title)

    new_appointment = Appointment(
        first_name=first_name,
        last_name=last_name,
        title=title,
        date_time_from=date_time_from,
        date_time_to=date_time_to
    )

    db.session.add(new_appointment)
    db.session.commit()

    return jsonify(message=success_message),201


## Updating Appointments
@app.route('/update_appointments/<int:id>', methods=['PUT','OPTIONS'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
def update_appointments(id:int):
    print(f'{id}')
    record_id = int(id)
    record = Appointment.query.filter_by(id=record_id).first()
    print(request.json)
    if record:
        date = request.json['date']
        time_from = request.json['time_from']
        time_to = request.json['time_to']

        if date == '' or time_from == '' or time_to == '':
            return jsonify(message='date and time cannot be blank'), 406

        try:
            date_time_from = datetime.datetime.strptime(f'{date}T{time_from}', '%Y-%m-%dT%H:%M:%S')
            date_time_to = datetime.datetime.strptime(f'{date}T{time_to}', '%Y-%m-%dT%H:%M:%S')
        except:
            date_time_from = datetime.datetime.strptime(f'{date}T{time_from}', '%Y-%m-%dT%H:%M')
            date_time_to = datetime.datetime.strptime(f'{date}T{time_to}', '%Y-%m-%dT%H:%M')

        recieved_dates = DateTimeRange(f'{date}T{time_from}', f'{date}T{time_to}')

        ## any booking for the past dates or time cannot be accomodated.
        if datetime.datetime.now() > date_time_from:
            return jsonify(message='Any booking for the past dates or time cannot be accomodated'), 406
        if date_time_from > date_time_to:
            return jsonify(message='Any booking for the past dates or time cannot be accomodated'), 406

        ## booking are'nt allowed during sunday
        if datetime.datetime.strptime(date, '%Y-%m-%d').weekday() == 6:
            return jsonify(message='Sorry appointments are only allowed from Monday to Saturday'), 406

        ## bookings only allowed during opening-hourse
        opening_hours = DateTimeRange(f'{date}T09:00', f'{date}T17:00')
        if (recieved_dates in opening_hours) == False:
            return jsonify(message='Appointments are only allowed from 9:00AM - 5:00PM'), 406

        ## check for conflicting booking records
        success_message = 'You added a new record!'
        datas = Appointment.query.all()
        if datas:
            for data in datas:

                data_dates = DateTimeRange(str(data.date_time_from).replace(' ', 'T'),
                                           str(data.date_time_to).replace(' ', 'T'))
                if data_dates.is_intersection(recieved_dates):
                    if data.id != record_id:
                        return jsonify(message='There is a conflict between your schedule'), 409

        ## update records to the database
        record.first_name = request.json['first_name']
        record.last_name = request.json['last_name']
        record.title = request.json['title']
        record.date_time_from = date_time_from
        record.date_time_to = date_time_to

        db.session.commit()
        return jsonify(message="You updated a record"), 202
    else:
        return jsonify(message="record cannot be found!"), 404


## Show Appointments
@app.route('/show_appointments', methods=['POST','OPTIONS'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
def show_appointments():
    date_from = request.json['date_from']
    date_to = request.json['date_to']
    if date_from == '':
        date_from = str(datetime.datetime.now().date())
    if date_to == '':
        date_to = str(datetime.datetime.now().date())
    print(date_from, date_to)
    _date_from = datetime.datetime.strptime(f'{date_from}T09:00', '%Y-%m-%dT%H:%M')
    _date_to = datetime.datetime.strptime(f'{date_to}T17:00', '%Y-%m-%dT%H:%M')
    data = Appointment.query.filter(Appointment.date_time_from <= _date_to).filter(Appointment.date_time_from >= _date_from).order_by(Appointment.date_time_from.asc())
    result = appointments_schema.dump(data)
    result_sorted = sorted(result, key=lambda r: datetime.datetime.strptime(r["date_time_from"], "%Y-%m-%dT%H:%M:%S"))
    # print(result_sorted)
    return jsonify(result_sorted)


## Show only one appointment
@app.route('/appointment_details/<int:appointment_id>', methods=['GET','OPTIONS'])
@cross_origin(origin='*',headers=['Content-Type','Authorization'])
def appointment_details(appointment_id:int):
    data = Appointment.query.filter_by(id=appointment_id).first()
    if data:
        result = appointment_schema.dump(data)
        print(jsonify(result))
        return jsonify(result),200
    else:
        return jsonify(message='record not found'),404



## Delete Appointments
@app.route('/delete_appointments/<int:record_id>', methods=['DELETE','OPTIONS'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization','Access-Control-Allow-Methods'])
def delete_appointments(record_id:int):
    data = Appointment.query.filter_by(id=record_id).first()
    if data:
        db.session.delete(data)
        db.session.commit()
        return jsonify(message='You deleted a record'),202
    else:
        return jsonify(message='That record does not exist'),404



## Setting up DB Models
class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    title = Column(Text)
    date_time_from = Column(DateTime)
    date_time_to = Column(DateTime)

## Setting up Schema
class AppointmentSchema(ma.Schema):
    class Meta:
        fields = ('id','first_name','last_name','title','date_time_from','date_time_to')

## Instantiate Schema
## defining a schema for use if one data or many to deserialize our db
appointment_schema = AppointmentSchema()
appointments_schema = AppointmentSchema(many=True)

if __name__ == '__main__':
    app.run()