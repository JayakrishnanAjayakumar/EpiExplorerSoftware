from peewee import *
from peewee import chunked
import os
from playhouse.shortcuts import model_to_dict, dict_to_model
import json
import csv
from dateutil import parser
cwd=os.getcwd()
DATABASE=cwd+'/data/haiti_experimental.db'
database = SqliteDatabase(DATABASE)
class BaseModel(Model):
    class Meta:
        database = database
#SamplePoint bean
class SamplePoint (BaseModel):
    code=CharField(primary_key=True)
    neighborhood=CharField(null=True)
    type_=TextField(null=True)
    address=TextField(null=True)
    position=CharField(null=True)
    category=CharField(null=True)
    reservoircapacity=CharField(null=True)
    resrvoirwithtap=CharField(null=True)
    covered=CharField(null=True)
    waterusedfordrinking=CharField(null=True)
    waterusedforbathwash=CharField(null=True)
    image=CharField(null=True)
    def to_json(self):
        return json.dumps(model_to_dict(self))
    def to_dict(self):
        return model_to_dict(self)   
#ExperimentalRecord bean
class ExperimentalRecord(BaseModel):
    scode=ForeignKeyField(SamplePoint, backref='exprecords')
    do=FloatField(null=True)
    temp=FloatField(null=True)
    cond=FloatField(null=True)
    tds=FloatField(null=True)
    salinity=FloatField(null=True)
    ph=FloatField(null=True)
    coliform=FloatField(null=True)
    cholerae=FloatField(null=True)
    residualchlorine=FloatField(null=True)
    date=DateField(null=True)
    fuzzy=CharField(null=True)
    def to_dict(self):
        return model_to_dict(self)
    def to_json(self):
        dictvals=model_to_dict(self)
        dictvals['date']=dictvals['date'].strftime("%Y-%m-%d")
        return json.dumps(dictvals)

class SamplePoint_Log(BaseModel):
    code=CharField()
    type_=TextField(null=True)
    category=CharField(null=True)
    position=CharField(null=True)
    added_date=DateTimeField(null=True)

class EnvironmentalRecord(BaseModel):
    scode=ForeignKeyField(SamplePoint, backref='envrecords')
    date=DateField(null=True)
    water=FloatField(null=True)
    mud=FloatField(null=True)
    trash=FloatField(null=True)
    activity=FloatField(null=True)
    image=CharField(null=True)
    def to_dict(self):
        return model_to_dict(self)
    def to_json(self):
        dictvals=model_to_dict(self)
        dictvals['date']=dictvals['date'].strftime("%Y-%m-%d")
        return json.dumps(dictvals)

class WeatherStation(BaseModel):
    name=CharField(primary_key=True)
    address=CharField(null=True)
    location=CharField(null=True)
    
class WeatherRecords(BaseModel):
    sname = ForeignKeyField(WeatherStation, backref='stationname')
    timestamp=DateTimeField(null=True)
    rain=FloatField(null=True)
    temp=FloatField(null=True)
    rh=FloatField(null=True)
    
#helper method to convert dictionaries to SamplePoint
def generateSamplePointFromData(jsondata):
    return dict_to_model(SamplePoint, jsondata)

#helper method to convert dictionaries to ExperimentalRecord
def generateExperimentalRecordFromData(jsondata):
    return dict_to_model(ExperimentalRecord, jsondata)


            
    
