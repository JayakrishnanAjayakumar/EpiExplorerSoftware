import design
from PyQt5.QtWidgets import QApplication, QMainWindow,QFileDialog
from PyQt5.QtCore import QUrl
from PyQt5 import QtWebKit
import os
import sys
from PyQt5.QtCore import pyqtSlot
from samplepoint import *
import json
import re
import pickle
from dateutil import parser
import datetime
import math
from shutil import copy2
import csv
from collections import OrderedDict
import fiona
import fiona.crs
from shapely.geometry import Point, mapping
from random import randint
from fastkml import kml
from datetime import timedelta
import numpy as np
import operator
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
from glob import glob
import matplotlib.pyplot as plt
from matplotlib import rc
import matplotlib.dates as mdates
import matplotlib
import datetime
import base64
from fiona import _shim, schema
wgs84 = fiona.crs.from_epsg(4326)
floatvaluere=re.compile(r'[^\d.]+')
shapeschema={'geometry': 'Point','properties': {'code':'str','neighborhood':'str','type_':'str','category':'str','address':'str',
                                                'position':'str','reservoircapacity':'str','resrvoirwithtap':'str',
                                                'covered':'str','waterusedfordrinking':'str','waterusedforbathwash':'str',
                                                'date':'str','do':'float','temp': 'float','cond':'float',
                                                'tds':'float','salinity':'float','ph':'float',
                                                'coliform':'float','cholerae':'float','residualchlorine':'float',
                                                'fuzzy':'str','water':'float','mud':'float','activity':'float','trash':'float'}}
#helper method to generate image filenames on the fly
def generateRecordFileName(filename,sid,date):
    filename, file_extension = os.path.splitext(filename)
    image_file_name=str(sid)+date.replace('-','_')+file_extension
    imgdir=os.getcwd()+'/data/recordimages/'
    return imgdir+image_file_name

#helper method to process a KML placemark
def processPlaceMark(placemark,alldata):
    data={'name':placemark.name,'description':placemark.description}
    data['type']=placemark.geometry.type
    if placemark.geometry.type=='Point':
        data['coordinates']={'lat':placemark.geometry.coords[0][1],'lng':placemark.geometry.coords[0][0]}
    if placemark.geometry.type=='LineString':
        coordinates=[]
        for coord in placemark.geometry.coords:
            coordinates.append({'lat':coord[1],'lng':coord[0]})
        data['coordinates']=coordinates
    if placemark.geometry.type=='Polygon':
        coordinates=[]
        for coord in placemark.geometry.exterior.coords:
            coordinates.append({'lat':coord[1],'lng':coord[0]})
        data['coordinates']=coordinates
    alldata.append(data)

#helper method to process a KML folder
def processFolder(folder,alldata):
    features=list(folder.features())
    for feature in features:
        if isinstance(feature,kml.Folder):
            processFolder(feature,alldata)
            continue
        if isinstance(feature,kml.Placemark):
            processPlaceMark(feature,alldata)

#helper method for float conversion in records
def getValidRecordFloat(strval):
    val=strval.strip()
    fval='Error'
    if len(val)==0:
        return None
    cleanedval=floatvaluere.sub('',val)
    try:
        fval=float(cleanedval)
    except:
        fval='Error'
    return fval

class Explorer(QMainWindow, design.Ui_MainWindow):

    def __init__(self, parent=None):
        super(Explorer, self).__init__(parent)
        self.setupUi(self)
        cwd = os.getcwd()
        self.webView.settings().setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)
        self.webView.load(QUrl('file:///'+cwd+'/working/Explorer.html'))
        self.webView.loadFinished.connect(self.finishLoading)
        self.data={}
        self.imgfname=None
        self.sampimgfname=None
        self.outputfolder=None
    @pyqtSlot()
    def finishLoading(self):
        self.webView.page().mainFrame().addToJavaScriptWindowObject("exp", self)

    #adds a new sample point to the existing datastrcture
    @pyqtSlot('QVariantMap',result=str)
    def createNewSamplePoint(self,samplepoint):
        message="Sample Point added successfully"
        s=SamplePoint()
        s.create(**samplepoint)
        #we need to generate the image if it is available
        if len(samplepoint['image'])!=0:
            try:
                filename, file_extension = os.path.splitext(samplepoint['image'])
                newfilename=os.getcwd()+'/data/recordimages/'+samplepoint['code']+file_extension
                #check if this file exists, if so delete the file and create a new one
                if os.path.exists(newfilename):
                    os.remove(newfilename)
                copy2(samplepoint['image'],newfilename)
            except:
                message="Sample Point added successfully But image couldn't be added"
        return message
    
    #checks if an id exist in the dataset
    @pyqtSlot(str,result=str)
    def checkIdExists(self,samplepointId):
        query = SamplePoint.select().where(SamplePoint.code == samplepointId)
        if query.exists():
            return "Y"
        else:
            return "N"
        
    #gets sample point information other than records for a sample point using it's id 
    @pyqtSlot(str,result=str)
    def getSamplePointInfoForId(self,samplepointId):
        sobj=SamplePoint.get_by_id(samplepointId)
        self.sampimgfname=sobj.image
        return sobj.to_json()
        
    #update sample point
    @pyqtSlot('QVariantMap',result=str)
    def updateExistingSamplePoint(self,samplepoint):
        #get existing sample point for comparison
        sobj=SamplePoint.get_by_id(samplepoint['code'])
        if sobj.type_!=samplepoint['type_'] or sobj.category!=samplepoint['category'] or sobj.position!=samplepoint['position']:
            s=SamplePoint_Log()
            s.create(code=sobj.code,type_=sobj.type_,category=sobj.category,position=sobj.position,added_date=datetime.datetime.now())
        existingfname=None
        if self.sampimgfname is not None and len(self.sampimgfname)!=0:
            filename, file_extension = os.path.splitext(self.sampimgfname)
            existingfname=os.getcwd()+'/data/recordimages/'+samplepoint['code']+file_extension
        if len(samplepoint['image'])==0:
            #if there was a file existing delete it
            if existingfname is not None:
                #delete the existing image
                if os.path.exists(existingfname):
                    os.remove(existingfname)
        else:
            #check if both the file names are same if there is already an existing name
            if existingfname is not None:
                old_name=os.path.basename(self.sampimgfname)
                new_name=os.path.basename(samplepoint['image'])
                #we need to do a replace
                if old_name!=new_name:
                    if os.path.exists(existingfname):
                        os.remove(existingfname)
                    filename, file_extension = os.path.splitext(samplepoint['image'])
                    newname=os.getcwd()+'/data/recordimages/'+samplepoint['code']+file_extension
                    copy2(samplepoint['image'],newname)
            else:
                #create a fresh one
                filename, file_extension = os.path.splitext(samplepoint['image'])
                newname=os.getcwd()+'/data/recordimages/'+samplepoint['code']+file_extension
                copy2(samplepoint['image'],newname)
        s=SamplePoint(**samplepoint)
        s.save()
        return "Sample Point updated successfully"
    
    #delete sample point using id
    @pyqtSlot(str,result=str)
    def deleteExistingSamplePoint(self,samplepointId):
        #delete records first
        self.deleteAllRecordsForSamplePoint(samplepointId)
        self.deleteAllEnvRecordsForSamplePoint(samplepointId)
        samp=SamplePoint.get(SamplePoint.code == samplepointId)
        if samp.image is not None and len(samp.image)!=0:
            filename, file_extension = os.path.splitext(samp.image)
            fname=os.getcwd()+'/data/recordimages/'+samplepointId+file_extension
            #check if this file exists, if so delete
            if os.path.exists(fname):
                os.remove(fname)
        query = SamplePoint.delete().where(SamplePoint.code == samplepointId)
        query.execute()
        return "Sample point "+str(samplepointId)+" is deleted successfully"

    @pyqtSlot(str)
    def deleteAllRecordsForSamplePoint(self,samplepointId):
        #delete all records for a sample point
        query = ExperimentalRecord.delete().where(ExperimentalRecord.scode == samplepointId)
        return query.execute()

    @pyqtSlot(str)
    def deleteAllEnvRecordsForSamplePoint(self,samplepointId):
        #delete all records for a sample point
        query= EnvironmentalRecord.select(EnvironmentalRecord.image.alias('image'),EnvironmentalRecord.scode.alias('scode'),EnvironmentalRecord.date.alias('date')).where(EnvironmentalRecord.scode == samplepointId)
        for dat in query:
            if dat.image is not None and len(dat.image)!=0:
                fname=generateRecordFileName(str(dat.image),str(dat.scode),str(dat.date))
                #check if this file exists, if so delete the file and create a new one
                if os.path.exists(fname):
                    os.remove(fname)
        query = EnvironmentalRecord.delete().where(EnvironmentalRecord.scode == samplepointId)
        return query.execute()
    
    #check if a record exist in a samplepoint
    @pyqtSlot(str,str,result=str)
    def checkRecordExists(self,samplepointId,date):
        key=parser.parse(date)
        query = ExperimentalRecord.select().where((ExperimentalRecord.date==key) & (ExperimentalRecord.scode == samplepointId))
        if query.exists():
            return "Y"
        return "N"

    #check if env record exist for a samplepoint
    @pyqtSlot(str,str,result=str)
    def checkEnvRecordExists(self,samplepointId,date):
        key=parser.parse(date)
        query = EnvironmentalRecord.select().where((EnvironmentalRecord.date==key) & (EnvironmentalRecord.scode == samplepointId))
        if query.exists():
            return "Y"
        return "N"
    
    #helper method for validating the records, returns a dictionary with key as record attribute and value as the error.
    def getErrorsForTheRecord(self,record):
        errors={}
        #validate dioxide
        if getValidRecordFloat(record['do']) =='Error':
            errors['do']="The do value should be a valid real number"
        #validate temp
        if getValidRecordFloat(record['temp']) =='Error':
            errors['temp']="The temp value should be a valid real number"
        #validate cond
        if getValidRecordFloat(record['cond']) =='Error':
            errors['cond']="The cond value should be a valid real number"
        #validate tds
        if getValidRecordFloat(record['tds']) =='Error':
            errors['tds']="The tds value should be a valid real number"
        #validate salinity
        if getValidRecordFloat(record['salinity']) =='Error':
            errors['salinity']="The salinity value should be a valid real number"
        #validate ph
        if getValidRecordFloat(record['ph']) =='Error':
            errors['ph']="The ph value should be a valid real number"
        #validate coliform
        if getValidRecordFloat(record['coliform']) =='Error':
            errors['coliform']="The coliform value should be a valid real number"
        #validate cholerae
        if getValidRecordFloat(record['cholerae']) =='Error':
            errors['cholerae']="The cholerae value should be a valid real number"
        #validate residualchlorine
        if getValidRecordFloat(record['residualchlorine']) =='Error':
            errors['residualchlorine']="The residualchlorine value should be a valid real number"
        if len(record['date'])==0:
            errors['date']="Date is mandatory"
        return errors

    def getErrorsForTheEnvRecord(self,record):
        errors={}
        if getValidRecordFloat(record['water']) =='Error':
            errors['water']="The water value should be a valid real number"
        if getValidRecordFloat(record['trash']) =='Error':
            errors['trash']="The trash value should be a valid real number"
        if getValidRecordFloat(record['activity']) =='Error':
            errors['activity']="The activity value should be a valid real number"
        if getValidRecordFloat(record['mud']) =='Error':
            errors['mud']="The mud value should be a valid real number"
        if len(record['date'])==0:
            errors['date']="Date is mandatory"
        return errors
        
    #check if a record has valid fields
    @pyqtSlot('QVariantMap',result=str)
    def validateRecord(self,record):
        errordict=self.getErrorsForTheRecord(record)
        if len(errordict)==0:
            return ''
        else:
            errorstring=""
            for key in errordict:
                errorstring+=" "+key+":"+errordict[key]+"\n"
            return errorstring

    #check if a record has valid fields
    @pyqtSlot('QVariantMap',result=str)
    def validateEnvRecord(self,record):
        errordict=self.getErrorsForTheEnvRecord(record)
        if len(errordict)==0:
            return ''
        else:
            errorstring=""
            for key in errordict:
                errorstring+=" "+key+":"+errordict[key]+"\n"
            return errorstring
        
    #add a new record
    @pyqtSlot('QVariantMap',result=str)
    def createNewRecord(self,record):
        if record['coliform'].startswith('<') or record['coliform'].startswith('>'):
            record['fuzzy']='Y'
        else:
            record['fuzzy']='N'
        for attr in record:
            if attr not in ['scode','date','fuzzy']:
                record[attr]=getValidRecordFloat(record[attr])
        e=ExperimentalRecord()
        e.create(**record)
        return "New Record Added to the sample point"

    #add a new env record
    @pyqtSlot('QVariantMap',result=str)
    def createNewEnvRecord(self,record):
        message="New Environmental Record Added to the sample point"
        for attr in record:
            if attr not in ['scode','date','image']:
                record[attr]=getValidRecordFloat(record[attr])
        e=EnvironmentalRecord()
        e.create(**record)
        #we need to generate the image if it is available
        if len(record['image'])!=0:
            try:
                filename=generateRecordFileName(record['image'],record['scode'],record['date'])
                #check if this file exists, if so delete the file and create a new one
                if os.path.exists(filename):
                    os.remove(filename)
                copy2(record['image'],filename)
            except:
                message="New Environmental Record Added But image couldn't be added"
        return message

    #get record
    @pyqtSlot(str,str,result=str)
    def getRecord(self,samplepointId,date):
        key=parser.parse(date)
        rec=ExperimentalRecord.get((ExperimentalRecord.date==key),(ExperimentalRecord.scode == samplepointId))
        return rec.to_json()

    #get record
    @pyqtSlot(str,str,result=str)
    def getEnvRecord(self,samplepointId,date):
        key=parser.parse(date)
        rec=EnvironmentalRecord.get((EnvironmentalRecord.date==key),(EnvironmentalRecord.scode == samplepointId))
        self.imgfname=rec.image
        return rec.to_json()
    
    #update an existing record
    @pyqtSlot('QVariantMap',result=str)
    def updateExistingRecord(self,record):
        if record['coliform'].startswith('<') or record['coliform'].startswith('>'):
            record['fuzzy']='Y'
        else:
            record['fuzzy']='N'
        for attr in record:
            if attr not in ['scode','date','fuzzy']:
                record[attr]=getValidRecordFloat(record[attr])
        #delete existing and insert
        self.deleteExistingRecord(record['scode'],record['date'])
        e=ExperimentalRecord()
        e.create(**record)   
        return "Record updated with new values"

    #update an existing environmental record
    @pyqtSlot('QVariantMap',result=str)
    def updateExistingEnvRecord(self,record):
        for attr in record:
            if attr not in ['scode','date','image']:
                record[attr]=getValidRecordFloat(record[attr])
        #delete existing and insert
        self.deleteExistingEnvRecord(record['scode'],record['date'],deleteFile=False)
        e=EnvironmentalRecord()
        e.create(**record)
        message="Environmental Record updated with new values"
        existingfname=None
        if self.imgfname is not None and len(self.imgfname)!=0:
            existingfname=generateRecordFileName(self.imgfname,record['scode'],record['date'])
        if len(record['image'])==0:
            #if there was a file existing delete it
            if existingfname is not None:
                #delete the existing image
                if os.path.exists(existingfname):
                    os.remove(existingfname)
        else:
            #check if both the file names are same if there is already an existing name
            if existingfname is not None:
                old_name=os.path.basename(self.imgfname)
                new_name=os.path.basename(record['image'])
                #we need to do a replace
                if old_name!=new_name:
                    if os.path.exists(existingfname):
                        os.remove(existingfname)
                    newname=generateRecordFileName(record['image'],record['scode'],record['date'])
                    copy2(record['image'],newname)
            else:
                #create a fresh one
                newname=generateRecordFileName(record['image'],record['scode'],record['date'])
                copy2(record['image'],newname)
        return message
    
    #get record dates for the sample point
    @pyqtSlot(str,result=str)
    def getRecordDatesForSamplePoints(self,samplepointId):
        dates=[]
        query = ExperimentalRecord.select().where(ExperimentalRecord.scode == samplepointId).order_by(ExperimentalRecord.date)
        for erec in query:
            dates.append(erec.date.strftime("%Y-%m-%d"))
        return json.dumps(dates)

    #get env record dates for the sample point
    @pyqtSlot(str,result=str)
    def getEnvRecordDatesForSamplePoints(self,samplepointId):
        dates=[]
        query = EnvironmentalRecord.select().where(EnvironmentalRecord.scode == samplepointId).order_by(EnvironmentalRecord.date)
        for erec in query:
            dates.append(erec.date.strftime("%Y-%m-%d"))
        return json.dumps(dates)
    
    #delete a record
    @pyqtSlot(str,str,result=str)
    def deleteExistingRecord(self,samplepointId,date):
        key=parser.parse(date)
        query=ExperimentalRecord.delete().where((ExperimentalRecord.date==key) & (ExperimentalRecord.scode == samplepointId))
        query.execute()
        return "Record deleted successfully"

    #delete a env record
    @pyqtSlot(str,str,result=str)
    def deleteExistingEnvRecord(self,samplepointId,date,deleteFile=True):
        key=parser.parse(date)
        record=EnvironmentalRecord.get((EnvironmentalRecord.date==key),(EnvironmentalRecord.scode == samplepointId))
        imgfile=record.image
        scode=str(record.scode)
        date=str(record.date)
        query=EnvironmentalRecord.delete().where((EnvironmentalRecord.date==key) & (EnvironmentalRecord.scode == samplepointId))
        query.execute()
        if deleteFile:
            if imgfile is not None and len(imgfile)!=0:
                fname=generateRecordFileName(imgfile,scode,date)
                if os.path.exists(fname):
                    os.remove(fname)
        return "Environmental Record deleted successfully"

    #load all the sample point instances
    @pyqtSlot(result=str)
    def loadAllSamplePointInstances(self):
        data=[]
        query=SamplePoint.select()
        for sampoint in query:
            data.append(sampoint.to_json())
        return json.dumps(data)

    #Get visualization data based on parameters.
    @pyqtSlot('QVariantMap',result=str)
    def getVisualizationData(self,visualizationParameters):
        date=parser.parse(visualizationParameters['date'],fuzzy=True)
        #fuzzy query
        before=date-timedelta(days=3)
        after=date+timedelta(days=3)
        samplepointdetails=SamplePoint.get(SamplePoint.code==visualizationParameters['code'])
        if 'category' not in visualizationParameters:
            category=samplepointdetails.category
        else:
            category=visualizationParameters['category']
        if 'neighborhood' not in visualizationParameters:
            neighborhood=samplepointdetails.neighborhood
        else:
            neighborhood=visualizationParameters['neighborhood']
        #all codes from the same category
        all_same_categ=SamplePoint.select(SamplePoint.code).where(SamplePoint.category==category)
        #all codes from the same category for the same neighborhood
        all_same_categ_neighb=SamplePoint.select(SamplePoint.code).where((SamplePoint.category==category) & (SamplePoint.neighborhood==neighborhood))
        query_all_same_categ=ExperimentalRecord.select().where(((ExperimentalRecord.date<=after)&(ExperimentalRecord.date>=before))&(ExperimentalRecord.scode.in_(all_same_categ))&(ExperimentalRecord.coliform.is_null(False))).order_by(ExperimentalRecord.coliform.desc())
        query_all_same_categ_neighb=ExperimentalRecord.select().where(((ExperimentalRecord.date<=after)&(ExperimentalRecord.date>=before))&(ExperimentalRecord.scode.in_(all_same_categ_neighb))&(ExperimentalRecord.coliform.is_null(False))).order_by(ExperimentalRecord.coliform.desc())
        query_all_year=ExperimentalRecord.select().where((ExperimentalRecord.scode==visualizationParameters['code'])&(ExperimentalRecord.coliform.is_null(False))).order_by(ExperimentalRecord.date)
        all_same_categ_data=[[str(recs.scode),float(recs.coliform),math.floor(float(recs.coliform)),recs.date.strftime("%Y-%m-%d")] for recs in query_all_same_categ]
        if len(all_same_categ_data)!=0 and all_same_categ_data[0][1]!=0:
            #we will do log transformation here
            maxim=math.log(all_same_categ_data[0][1],10)
            for i in range(len(all_same_categ_data)):
                if all_same_categ_data[i][1]!=0:
                    all_same_categ_data[i][1]=(math.log(all_same_categ_data[i][1],10)/maxim)
        all_same_categ_neighb_data=[str(recs.scode) for recs in query_all_same_categ_neighb]
        all_year_data=[[recs.date.strftime("%Y-%m-%d"),float(recs.coliform),math.floor(float(recs.coliform))] for recs in query_all_year]
        if len(all_year_data)!=0:
            maxval=max(all_year_data,key=lambda x:x[1])[1]
            if maxval!=0:
                maxval=math.log(maxval,10)
                for i in range(len(all_year_data)):
                    if all_year_data[i][1]!=0:
                        all_year_data[i][1]=(math.log(all_year_data[i][1],10)/maxval)
        out=json.dumps({'date':visualizationParameters['date'],'categdata':all_same_categ_data,'datedata':all_year_data,'category':category,'neighborhooddata':all_same_categ_neighb_data,'neighborhood':neighborhood,'sid':visualizationParameters['code']})
        return out

    #get all sample points for a category
    @pyqtSlot(str,result=str)
    def getAllSamplePointsForCategory(self,category):
        query=SamplePoint.select().where(SamplePoint.category==category)
        return json.dumps([s.code for s in query])

    #get all neighborhoods
    @pyqtSlot(result=str)
    def getAllNeighborhoods(self):
        query=SamplePoint.select()
        return json.dumps(list(set([s.neighborhood for s in query])))

    #get all neighborhoods
    @pyqtSlot(str,result=str)
    def getAllCategsForNeighborhood(self,neighborhood):
        query=SamplePoint.select().where(SamplePoint.neighborhood==neighborhood)
        return json.dumps(list(set([s.category for s in query])))

    #get data based on neighborhood and category
    @pyqtSlot('QVariantMap',result=str)
    def getDataForNeighborhoodAndCategory(self,neighbData):
        neighborhood=neighbData['neighborhood']
        category=neighbData['category']
        query=SamplePoint.select(SamplePoint.code).where((SamplePoint.category==category)&(SamplePoint.neighborhood==neighborhood))
        query1=ExperimentalRecord.select(ExperimentalRecord.scode.alias('scode'),fn.avg(ExperimentalRecord.coliform).alias('colavg')).where(ExperimentalRecord.scode.in_(query)).group_by(ExperimentalRecord.scode).order_by(fn.avg(ExperimentalRecord.coliform))
        data=[[str(s.scode),max(1,int(math.floor(s.colavg)))] for s in query1]
        return json.dumps(data)

    #get all categories
    @pyqtSlot(result=str)
    def getAllCategories(self):
        query=SamplePoint.select()
        return json.dumps((list(set([j.category for j in query]))))

    #get sample points for neighborhood with category
    @pyqtSlot(str,str,result=str)
    def getSamplePointsForNeighborhoodCategory(self,neighborhood,category):
        query=SamplePoint.select(SamplePoint.code).where((SamplePoint.category==category)&(SamplePoint.neighborhood==neighborhood))
        return json.dumps([s.code for s in query])

    #open image file
    @pyqtSlot(result=str)
    def openImageFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select Image File",
                '', "Images (*.tif *.TIF *.jpg *.JPG .jpeg .JPEG .gif .GIF .png .PNG)")
        return fileName

    #get coordinates for sample point
    '''@pyqtSlot(str,result=str)
    def getCoordinatesForId(self,sid):
        sp=SamplePoint.get_by_id(sid)
        return json.dumps(sp.position.split(','))'''
    
    #upload kml file
    @pyqtSlot(result=str)
    def uploadKMLFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select KML File",
                '', "KML Files (*.kml *.KML)")
        if fileName is None or len(fileName)==0:
            return ''
        with open(fileName) as kmlfile:
            data=kmlfile.read()
        kmlobj = kml.KML()
        xml = bytes(bytearray(data, encoding='utf-8'))
        kmlobj.from_string(xml)
        allfeatures=list(list(kmlobj.features())[0].features())
        alldata=[]
        for feature in allfeatures:
            if isinstance(feature,kml.Folder):
                processFolder(feature,alldata)
                continue
            if isinstance(feature,kml.Placemark):
                processPlaceMark(feature,alldata)
        return json.dumps(alldata)

    @pyqtSlot(str,str,result=str)
    def getEnvValues(self,samplePointId,variable):
        outdata=[]
        query=EnvironmentalRecord.select().where(EnvironmentalRecord.scode==samplePointId).order_by(EnvironmentalRecord.date)
        for records in query:
            recorddict=records.to_dict()
            outdata.append([records.date.strftime("%Y-%m-%d"),recorddict[variable]])
        return json.dumps(outdata)

    @pyqtSlot(str,str,str,str,result=str)
    def getEnvSameNeighborhood(self,date,variable,category,neighborhood):
        dateval=parser.parse(date,fuzzy=True)
        before=dateval-timedelta(days=3)
        after=dateval+timedelta(days=3)
        outdata=[]
        querysid=SamplePoint.select(SamplePoint.code).where((SamplePoint.category==category)&(SamplePoint.neighborhood==neighborhood))
        query=EnvironmentalRecord.select().where(((EnvironmentalRecord.date>=before)&(EnvironmentalRecord.date<=after))&(EnvironmentalRecord.scode.in_(querysid)))
        for records in query:
            recorddict=records.to_dict()
            outdata.append([str(records.scode),recorddict[variable],records.date.strftime("%Y-%m-%d")])
        return json.dumps(outdata)

    @pyqtSlot(str,str,str,result=str)
    def getEnvAllNeighborhood(self,date,variable,category):
        dateval=parser.parse(date,fuzzy=True)
        before=dateval-timedelta(days=3)
        after=dateval+timedelta(days=3)
        outdata=[]
        querysid=SamplePoint.select(SamplePoint.code).where((SamplePoint.category==category))
        #query=EnvironmentalRecord.select(EnvironmentalRecord.scode,EnvironmentalRecord.date.alias('date'),SamplePoint.neighborhood.alias('neighborhood'),EnvironmentalRecord.mud.alias('mud'),EnvironmentalRecord.water.alias('water'),EnvironmentalRecord.trash.alias('trash'),EnvironmentalRecord.activity.alias('activity')).join(SamplePoint).where(EnvironmentalRecord.date>=before & EnvironmentalRecord.date<=after & EnvironmentalRecord.scode.in_(querysid))
        query=EnvironmentalRecord.select().where(((EnvironmentalRecord.date>=before)&(EnvironmentalRecord.date<=after))&(EnvironmentalRecord.scode.in_(querysid)))
        for records in query:
            recorddict=records.to_dict()
            outdata.append([str(records.scode),recorddict[variable],records.date.strftime("%Y-%m-%d"),SamplePoint.get_by_id(str(records.scode)).neighborhood])
        return json.dumps(outdata)
        
    #upload experimental record
    @pyqtSlot(result=str)
    def uploadExperimentalRecords(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select CSV Record File",
                '', "Data (*.csv *.CSV)")
        if fileName is not None and len(fileName.strip())!=0:
            recordsread=0
            errordat=OrderedDict()
            alldat=[]
            sitecodedate=[]
            with open(fileName, newline='') as datafile:
                reader = csv.DictReader(datafile)
                for row in reader:
                    recordsread+=1
                    #create a new dictionary with stripped and lower key values
                    newr={}
                    for k in row:
                        newr[k.strip().lower()]=row[k]
                    exp=ExperimentalRecord()
                    allkeys=exp.to_dict()
                    allkeys.pop('fuzzy',None)
                    allkeys.pop('id',None)
                    for key in allkeys:
                        if key not in newr.keys():
                            if recordsread not in errordat:
                                errordat[recordsread]=""
                            errordat[recordsread]+="The field "+str(key)+" is missing"
                    if recordsread not in errordat:
                        if SamplePoint.select().where(SamplePoint.code==newr['scode']).count()==0:
                            errordat[recordsread]="the Code '"+newr['scode']+"' is new and not yet in the database\n"
                            continue
                        try:
                            date= parser.parse(newr['date'])
                        except:
                            errordat[recordsread]="the date is not valid"
                            continue
                        newr['date']=date.strftime("%Y-%m-%d")
                        pkey=newr['scode']+newr['date']
                        if pkey in sitecodedate:
                            errordat[recordsread]="duplicate records in the same file"
                            continue
                        else:
                            sitecodedate.append(pkey)
                        if ExperimentalRecord.select().where((ExperimentalRecord.scode==newr['scode'])&(ExperimentalRecord.date==date)).count()!=0:
                            errordat[recordsread]="Record already exist in database"
                            continue
                    else:
                        continue
                    errorrecs=self.validateRecord(newr)
                    if len(errorrecs)!=0:
                        errordat[recordsread]=errorrecs
                        continue
                    alldat.append(newr)
            if len(errordat)!=0:
                errstring=""
                for keys in errordat:
                    errstring+="Line "+str(keys)+"["+errordat[keys]+"]\n"
                return errstring
            else:
                for record in alldat:
                    self.createNewRecord(record)
                return "All Experimental Records added successfully"

    #upload environmental record
    @pyqtSlot(result=str)
    def uploadEnvironmentalRecords(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select CSV Record File",
                '', "Data (*.csv *.CSV)")
        if fileName is not None and len(fileName.strip())!=0:
            recordsread=0
            errordat=OrderedDict()
            alldat=[]
            sitecodedate=[]
            with open(fileName, newline='') as datafile:
                reader = csv.DictReader(datafile)
                for row in reader:
                    recordsread+=1
                    #create a new dictionary with stripped and lower key values
                    newr={}
                    for k in row:
                        newr[k.strip().lower()]=row[k]
                    exp=EnvironmentalRecord()
                    allkeys=exp.to_dict()
                    allkeys.pop('image',None)
                    allkeys.pop('id',None)
                    for key in allkeys:
                        if key not in newr.keys():
                            if recordsread not in errordat:
                                errordat[recordsread]=""
                            errordat[recordsread]+="The field "+str(key)+" is missing"
                    if recordsread not in errordat:
                        if SamplePoint.select().where(SamplePoint.code==newr['scode']).count()==0:
                            errordat[recordsread]="the Code '"+newr['scode']+"' is new and not yet in the database\n"
                            continue
                        try:
                            date= parser.parse(newr['date'])
                        except:
                            errordat[recordsread]="the date is not valid"
                            continue
                        newr['date']=date.strftime("%Y-%m-%d")
                        pkey=newr['scode']+newr['date']
                        if pkey in sitecodedate:
                            errordat[recordsread]="duplicate records in the same file"
                            continue
                        else:
                            sitecodedate.append(pkey)
                        if EnvironmentalRecord.select().where((EnvironmentalRecord.scode==newr['scode'])&(EnvironmentalRecord.date==date)).count()!=0:
                            errordat[recordsread]="Record already exist in database"
                            continue
                    else:
                        continue
                    errorrecs=self.validateEnvRecord(newr)
                    if len(errorrecs)!=0:
                        errorstring=""
                        for key in errorrecs:
                            errorstring+=errorrecs[key]+"\n"
                        errordat[recordsread]=errorstring
                        continue
                    newr['image']=''
                    alldat.append(newr)
            if len(errordat)!=0:
                errstring=""
                for keys in errordat:
                    errstring+="Line "+str(keys)+"["+errordat[keys]+"]\n"
                return errstring
            else:
                for record in alldat:
                    self.createNewEnvRecord(record)
                return "All Environmental Records added successfully"

    #get image url for a spatial point
    @pyqtSlot(str,result=str)
    def getImageForData(self,sid):
        spoint=SamplePoint.get(SamplePoint.code==sid)
        if spoint.image is None or len(spoint.image)==0:
            return ''
        filename, file_extension = os.path.splitext(spoint.image)
        fname=os.getcwd()+'/data/recordimages/'+sid+file_extension
        if not os.path.exists(fname):
            return ''
        return os.path.basename(fname)+'?'+str(randint(1, 99999999))

    #get rainfalldata
    @pyqtSlot(str,str,result=str)
    def getRainFallData(self,date,samplePointId):
        #we have to use sample pointId to find the nearest station location. For now just using the single weather station
        weatherStation='w_clinic'
        dateval=parser.parse(date)
        start=dateval-datetime.timedelta(days=14)
        end=dateval+datetime.timedelta(days=1)
        outdata=[]
        query=WeatherRecords.select(WeatherRecords.timestamp.day.alias('day'),WeatherRecords.timestamp.month.alias('month'),WeatherRecords.timestamp.year.alias('year'),fn.AVG(WeatherRecords.temp)
        .alias('avgtemp')).where((WeatherRecords.timestamp>=start)&(WeatherRecords.timestamp<end)&(WeatherRecords.sname==weatherStation)).group_by(WeatherRecords.timestamp.day,WeatherRecords.timestamp.month,WeatherRecords.timestamp.year).order_by(WeatherRecords.timestamp)
        for wr in query:
            outdata.append([parser.parse(str(wr.year)+'-'+str(wr.month)+'-'+str(wr.day)).strftime("%Y-%m-%d"),wr.avgtemp])
        return json.dumps(outdata)
    
    #download shape file
    @pyqtSlot(str,str,str,result=str)
    def downloadShape(self,date,filename,folder):
        dateval=parser.parse(date)
        expquery=ExperimentalRecord.select().where((ExperimentalRecord.date.year==dateval.year)&(ExperimentalRecord.date.month==dateval.month))
        envquery=EnvironmentalRecord.select().where((EnvironmentalRecord.date.year==dateval.year)&(EnvironmentalRecord.date.month==dateval.month))
        if expquery.count()==0 and envquery.count()==0:
            return 'No Records found'
        spoints={}
        exprecords={}
        envrecords={}
        for exp in expquery:
            if exp.scode not in spoints:
                spoints[exp.scode]={}
            if exp.date not in spoints[exp.scode]:
                spoints[exp.scode][exp.date]={}
            spoints[exp.scode][exp.date]['exp']=exp
        for env in envquery:
            if env.scode not in spoints:
                spoints[env.scode]={}
            if env.date not in spoints[env.scode]:
                spoints[env.scode][env.date]={}
            spoints[env.scode][env.date]['env']=env
        outpath=folder+"/"+filename+".shp"
        with fiona.open(outpath, 'w', crs=wgs84, driver='ESRI Shapefile',
                schema=shapeschema) as layer:
            for sp in spoints:
                alldict={}
                spdat=SamplePoint.get(SamplePoint.code==sp)
                spdictvals=spdat.to_dict()
                spdictvals.pop('id',None)
                alldict.update(spdictvals)
                for types in spoints[sp]:
                    typevals=spoints[sp][types]
                    for obj in typevals:
                        dictvals=typevals[obj]
                        dictvals=dictvals.to_dict()
                        alldict.update(dictvals)
                    if 'env' not in typevals:
                        e=EnvironmentalRecord()
                        dictvals=e.to_dict()
                        dictvals.pop('date',None)
                        alldict.update(dictvals)
                    if 'exp' not in typevals:
                        e=ExperimentalRecord()
                        dictvals=e.to_dict()
                        dictvals.pop('date',None)
                        alldict.update(dictvals)
                alldict.pop('id',None)
                alldict.pop('scode',None)
                alldict.pop('image',None)
                alldict['date']=alldict['date'].strftime("%Y-%m-%d")
                coordinates=list(map(float,spdictvals['position'].split(',')))
                point=Point(coordinates[0],coordinates[1])
                layer.write({'geometry':mapping(point),'properties':alldict})
        return 'New Shape File Created'
    #select output folder
    @pyqtSlot(result=str)
    def selectOutputFolder(self):
        folderName = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if( not folderName):
            folderName=""
        return folderName

    @pyqtSlot(str,str,result=str)
    def downloadCanvas(self,canvasstring,filename):
        canvasdata=canvasstring.split(',',1)[1]
        canvasdecoded = base64.b64decode(canvasdata)
        with open(self.outputfolder+"\\"+filename+".png",'wb') as outf:
            outf.write(canvasdecoded)
        return "image downloaded"
    
    @pyqtSlot(str,result=str)
    def getSimilarityMatrices(self,queryObject):
        query=json.loads(queryObject)
        cat1data=self.getMatrixData(query['categories'][0],query)
        geometry=None
        if (query['geometry']['type']=='point'):
            geometry=Point(query['geometry']['coordinates'])
        #sort the category based on distance
        cat1data.sort(key=lambda x:x[1].distance(geometry))
        mat1vals=np.asarray([t[-1] for t in cat1data])
        subvals=np.abs(mat1vals.reshape(len(mat1vals),1)-np.asarray([mat1vals]*len(mat1vals)).reshape(len(mat1vals),len(mat1vals)))
        subvals=1-(subvals/np.max(subvals))
        cat2data=self.getMatrixData(query['categories'][1],query)
        cat2datadict={}
        for d in cat2data:
            cat2datadict[d[0]]=d[-1]
        cat2allvals=[]
        for dat in cat1data:
            if dat[0] in cat2datadict:
                cat2allvals.append(cat2datadict[dat[0]])
            else:
                cat2allvals.append(np.nan)
        cat2allvals=np.asarray(cat2allvals)
        subvals2=np.abs(cat2allvals.reshape(len(cat2allvals),1)-np.asarray([cat2allvals]*len(cat2allvals)).reshape(len(cat2allvals),len(cat2allvals)))
        subvals2=1-(subvals2/np.nanmax(subvals2))
        self.timeSeriesSimilarity()
    def getMatrixData(self,category,queryObject):
        categ,table=category.split('<>')
        year,month=queryObject['monthyear'].split('-')
        outdata=[]
        if (table=='env'):
            query=EnvironmentalRecord.select().join(SamplePoint,on=(SamplePoint.code==EnvironmentalRecord.scode)).where((EnvironmentalRecord.date.year==int(year))&(EnvironmentalRecord.date.month==int(month))&(SamplePoint.category=='Pipe/Cistern'))
            for dat in query:
                outdata.append([dat.scode.code,Point(tuple(map(float,dat.scode.position.split(',')))),EnvironmentalRecord.to_dict(dat)[categ]])
        else:
            query=ExperimentalRecord.select().join(SamplePoint,on=(SamplePoint.code==ExperimentalRecord.scode)).where((ExperimentalRecord.date.year==int(year))&(ExperimentalRecord.date.month==int(month))&(SamplePoint.category=='Pipe/Cistern'))
            for dat in query:
                outdata.append([dat.scode.code,Point(tuple(map(float,dat.scode.position.split(',')))),ExperimentalRecord.to_dict(dat)[categ]])
        return outdata

    def timeSeriesSimilarity(self):
        time_matrix={}
        query=ExperimentalRecord.select().join(SamplePoint,on=(SamplePoint.code==ExperimentalRecord.scode)).where((SamplePoint.category=='Pipe/Cistern')).order_by(ExperimentalRecord.date.asc())
        for dat in query:
            if dat.scode.code not in time_matrix:
                time_matrix[dat.scode.code]=OrderedDict()
            time_matrix[dat.scode.code][str(dat.date.year)+'-'+str(dat.date.month)]=dat.coliform
        corrmatrix={}
        for wp in time_matrix:
            corrmatrix[wp]={}
            timearr=time_matrix[wp]
            for wpo in time_matrix:
                if wp==wpo:
                    continue
                timearr2=time_matrix[wpo]
                a,b=[],[]
                matchkeys=list(set(timearr.keys()).intersection(set(timearr2.keys())))
                for key in matchkeys:
                    a.append(timearr[key])
                    b.append(timearr2[key])
                if len(a)<6:
                    continue
                    #corrmatrix[wp][wpo]='No-Data'
                else:
                    #a = (a - np.mean(a)) / (np.std(a) * len(a))
                    #b = (b - np.mean(b)) / (np.std(b))
                    #c = np.correlate(a, b, 'full')
                    #c=stats.pearsonr(a, b)
                    #c=np.corrcoef(a, b)
                    #if np.isnan(c[0,1]):
                    #    continue
                    c=np.sqrt(np.sum((np.asarray(a)-np.asarray(b))**2))
                    corrmatrix[wp][wpo]=c
        for key in corrmatrix:
            sorted_x = sorted(corrmatrix[key].items(), key=operator.itemgetter(1),reverse=False)
            corrmatrix[key]=sorted_x
        print (time_matrix['CTMS11'])
        print (time_matrix[corrmatrix['CTMS11'][1][0]])
        print (corrmatrix['CTMS11'])

    @pyqtSlot(result=str)
    def getAllMonthYear(self):
        query=ExperimentalRecord.select(ExperimentalRecord.date).order_by(ExperimentalRecord.date.asc())
        yearmonth=OrderedDict()
        for d in query:
            yearmonth[str(d.date.year)+"-"+str(d.date.month)]=""
        return json.dumps(list(yearmonth.keys()))

    @pyqtSlot(str,result=str)
    def getStats(self,spobjstring):
        queryobject=json.loads(spobjstring)
        geomdata=None
        metadata={}
        thismonthdata={}
        lastmonthdata={}
        neighb_categ={}
        categ_all={}
        timedata=parser.parse(queryobject['date'])
        lmtimedata=timedata+relativedelta(months=-1)
        if queryobject['type']=='Point':
            geomdata=Point(queryobject['coordinates'][0],queryobject['coordinates'][1])
        #perform the query
        query=ExperimentalRecord.select().join(SamplePoint,on=(SamplePoint.code==ExperimentalRecord.scode)).where((ExperimentalRecord.date.year==int(timedata.year))&(ExperimentalRecord.date.month==int(timedata.month))|(ExperimentalRecord.date.year==int(lmtimedata.year))&(ExperimentalRecord.date.month==int(lmtimedata.month)))
        for dat in query:
            if dat.scode.code not in metadata:
                metadata[dat.scode.code] = dat.scode
            if dat.date.year==timedata.year and dat.date.month==timedata.month:
                thismonthdata[dat.scode.code]=dat.coliform
                if dat.scode.neighborhood not in neighb_categ:
                    neighb_categ[dat.scode.neighborhood]={}
                if dat.scode.category not in neighb_categ[dat.scode.neighborhood]:
                    neighb_categ[dat.scode.neighborhood][dat.scode.category]=[]
                neighb_categ[dat.scode.neighborhood][dat.scode.category].append([dat.scode.code,dat.coliform])
                if dat.scode.category not in categ_all:
                    categ_all[dat.scode.category]=[]
                categ_all[dat.scode.category].append([dat.scode.code,dat.coliform]) 
            elif dat.date.year==lmtimedata.year and dat.date.month==lmtimedata.month:
                lastmonthdata[dat.scode.code]=dat.coliform
        #sort all the ranks
        for neighbhood in neighb_categ:
            for categ in neighb_categ[neighbhood]:
                neighb_categ[neighbhood][categ].sort(key=lambda r:r[1],reverse=True)
        for categ in categ_all:
            categ_all[categ].sort(key=lambda r:r[1],reverse=True)
        alldata=[]
        for spoint in thismonthdata:
            dat={'name':spoint}
            #previous month change
            prevmonthchange="N/A"
            if spoint in lastmonthdata and lastmonthdata[spoint]!=0:
                prevmonthchange=int(((thismonthdata[spoint]-lastmonthdata[spoint])*100)/lastmonthdata[spoint])
            dat['perc_change']=prevmonthchange
            dat['neighb_rank']=str(neighb_categ[metadata[spoint].neighborhood][metadata[spoint].category].index([spoint,thismonthdata[spoint]])+1)+" of "+str(len(neighb_categ[metadata[spoint].neighborhood][metadata[spoint].category]))
            dat['categ_rank']=str(categ_all[metadata[spoint].category].index([spoint,thismonthdata[spoint]])+1)+" of "+str(len(categ_all[metadata[spoint].category]))
            dat['category']=metadata[spoint].category
            dat['neighborhood']=metadata[spoint].neighborhood
            dat['position']=metadata[spoint].position
            coli_log=0
            if thismonthdata[spoint]!=0:
                coli_log=np.log10(thismonthdata[spoint])
            dat['coliform_log']=round(coli_log,2)
            #assign the self_rank
            cvals=[]
            query=ExperimentalRecord.select(ExperimentalRecord.coliform).where(ExperimentalRecord.scode==spoint)
            for cnt in query:
                cvals.append(cnt.coliform)
            cvals.sort(reverse=True)
            dat['self_rank']=str(cvals.index(thismonthdata[spoint])+1)+" of "+str(len(cvals))
            alldata.append(dat)
        alldata.sort(key=lambda x:geomdata.distance(Point(float(x['position'].split(',')[0]),float(x['position'].split(',')[1]))))
        return json.dumps(alldata)
    
    @pyqtSlot(result=str)
    def getAllCategories(self):
        query=SamplePoint.select(SamplePoint.category).distinct()
        return json.dumps([d.category for d in query])

    @pyqtSlot(str,result=str)
    def getHeatmapData(self,hmapstring):
        hmapobject=json.loads(hmapstring)
        out=[]
        timedata=parser.parse(hmapobject['date'])
        category=hmapobject['category']
        neighborhood=hmapobject['neighborhood']
        if neighborhood=='All':
            query=ExperimentalRecord.select().join(SamplePoint,on=(SamplePoint.code==ExperimentalRecord.scode)).where((ExperimentalRecord.date.year==int(timedata.year))&(ExperimentalRecord.date.month==int(timedata.month))& (ExperimentalRecord.scode.category==category))
        else:
            query=ExperimentalRecord.select().join(SamplePoint,on=(SamplePoint.code==ExperimentalRecord.scode)).where((ExperimentalRecord.date.year==int(timedata.year))&(ExperimentalRecord.date.month==int(timedata.month))& (ExperimentalRecord.scode.category==category)&(ExperimentalRecord.scode.neighborhood==neighborhood))
        for d in query:
            coli_log=0
            if d.coliform!=0:
                coli_log=np.log10(d.coliform)
            out.append([d.scode.code,coli_log])
        return json.dumps(out)
    
    @pyqtSlot(str,result=str)
    def downloadStats(self,statobjstring):
        statobj=json.loads(statobjstring)
        currdate=parser.parse(statobj['dates']).date()
        spointrecord=SamplePoint.get(SamplePoint.code==statobj['pointid'])
        #check for image
        images=glob(os.getcwd()+'\\data\\recordimages\\*')
        img=None
        for image in images:
            if statobj['pointid'].lower()+'.' in image.lower():
                img=image
                break
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial",'B', size=14)
        pdf.cell(200, 8, txt=str(statobj['pointid']), ln=1, align="C")
        pdf.set_font("Arial",size=10)
        pdf.cell(200, 8, txt="Location (lat,lon): "+spointrecord.position, ln=1)
        pdf.cell(200, 8, txt="Address: "+spointrecord.address, ln=1)
        pdf.cell(200, 8, txt="Neighborhood: "+spointrecord.neighborhood, ln=1)
        pdf.cell(200, 8, txt="Category: "+spointrecord.category, ln=1)
        pdf.cell(200, 8, txt="Type: "+spointrecord.type_, ln=1)
        pdf.ln(5)
        if img is not None:
            pdf.image(img,w=30*1.618,h=30,x=80)
        pdf.ln(3)
        #make the first chart, for total coliform
        query=ExperimentalRecord.select().where(ExperimentalRecord.scode==statobj['pointid']).order_by(ExperimentalRecord.date.asc())
        dateexpcolidata=np.asarray([[t.date,t.coliform if t.coliform==0 else round(np.log10(t.coliform),2)]for t in query])
        #plot the coliform data
        rc('font', weight='bold')
        fig, ax = plt.subplots(figsize=(6.37008218, 3.93701))
        ax.plot(dateexpcolidata[:,0], dateexpcolidata[:,1], 'bo', dateexpcolidata[:,0], dateexpcolidata[:,1], 'b--')
        ind=np.where(dateexpcolidata[:,0]==currdate)
        selfrank=sorted(dateexpcolidata[:,1],reverse=True).index(dateexpcolidata[:,1][ind])+1
        ax.plot(dateexpcolidata[:,0][ind[0]], dateexpcolidata[:,1][ind[0]], 'ro')
        #coliform should be logscale
        ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%y'))
        plt.xlabel("Date",fontweight='bold')
        plt.title("Colifrom Count for "+statobj['pointid'])
        plt.ylabel("Coliform Count (Log10)",fontweight='bold')
        fig.autofmt_xdate()
        fig.savefig(os.getcwd()+'\\data\\TempImages\\all_coli.png',dpi=300)
        plt.close(fig)
        pdf.image(os.getcwd()+'\\data\\TempImages\\all_coli.png',w=60*1.618,h=60,x=60)
        query2=EnvironmentalRecord.select().where(EnvironmentalRecord.scode==statobj['pointid']).order_by(EnvironmentalRecord.date.asc())
        dateenvdata=np.asarray([[t.date,t.water,t.mud,t.trash,t.activity]for t in query2])
        ind=np.where(np.asarray(list(map(lambda x: str(x[0].year)+"-"+str(x[0].month), dateenvdata)))==str(currdate.year)+"-"+str(currdate.month))
        #plot the environmental data
        fig, axs = plt.subplots(2, 2, figsize=(9.708, 6))
        labels=['Water','Mud','Trash','Activity']
        for j in range(2):
            for i in range(2):
                axs[j,i].plot(dateenvdata[:,0], dateenvdata[:,(i+(2*j))+1], 'bo', dateenvdata[:,0], dateenvdata[:,(i+(2*j))+1], 'b--')
                axs[j,i].yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
                axs[j,i].xaxis.set_major_formatter(mdates.DateFormatter('%m-%y'))
                axs[j,i].set_ylim(0, 5)
                axs[j,i].set_ylabel(labels[(i+(2*j))], fontsize=14,fontweight='bold')
                if len (ind[0])!=0:
                    axs[j,i].plot(dateenvdata[:,0][ind[0]], dateenvdata[:,(i+(2*j))+1][ind[0]], 'ro')
                axs[j,i].xaxis.set_tick_params(labelsize=14)
                axs[j,i].yaxis.set_tick_params(labelsize=14)
        fig.suptitle('Environmental data for '+statobj['pointid'], fontsize=20)
        fig.autofmt_xdate()
        fig.savefig(os.getcwd()+'\\data\\TempImages\\all_env.png',dpi=300)
        plt.close(fig)
        pdf.ln(5)
        pdf.image(os.getcwd()+'\\data\\TempImages\\all_env.png',w=60*2,h=60,x=50)
        pdf.set_font("Arial",'B', size=14)
        pdf.cell(200, 8, txt=str(statobj['pointid'])+" on "+str(currdate), ln=1, align="C")
        pdf.set_font("Arial",size=10)
        query3=ExperimentalRecord.select(ExperimentalRecord.coliform).join(SamplePoint,on=(SamplePoint.code==ExperimentalRecord.scode)).where((ExperimentalRecord.date==currdate) & (ExperimentalRecord.scode==statobj['pointid']))
        colicount=0
        for k in query3:
            colicount=k.coliform
        pdf.cell(200, 8, txt="Coliform Count (Raw Count) : "+str(colicount), ln=1)
        pdf.cell(250, 8, txt="Coliform Count Rank Compared To Other Observations For "+statobj['pointid']+": "+str(selfrank)+" of "+str(len(dateexpcolidata[:,1])), ln=1)
        sameneighbquery=ExperimentalRecord.select().join(SamplePoint,on=(SamplePoint.code==ExperimentalRecord.scode)).where((ExperimentalRecord.date.year==currdate.year) & (ExperimentalRecord.date.month==currdate.month) & (ExperimentalRecord.scode.neighborhood==spointrecord.neighborhood) & (ExperimentalRecord.scode.category==spointrecord.category)).order_by(ExperimentalRecord.coliform.desc())
        rnk=1
        for d in sameneighbquery:
            if d.scode.code==spointrecord.code:
                break
            rnk+=1
        pdf.cell(200, 8, txt="Coliform Count Rank From Same Neighborhood For Same Category: "+str(rnk)+" of "+str(sameneighbquery.count()), ln=1)
        samecategquery=ExperimentalRecord.select().join(SamplePoint,on=(SamplePoint.code==ExperimentalRecord.scode)).where((ExperimentalRecord.date.year==currdate.year) & (ExperimentalRecord.date.month==currdate.month)  & (ExperimentalRecord.scode.category==spointrecord.category)).order_by(ExperimentalRecord.coliform.desc())
        rnk=1
        for d in samecategquery:
            if d.scode.code==spointrecord.code:
                break
            rnk+=1
        pdf.cell(200, 8, txt="Coliform Count Rank For Same Category: "+str(rnk)+" of "+str(samecategquery.count()), ln=1)
        threemonthdata=[]
        threemonthreldate=(datetime.datetime(currdate.year, currdate.month, 1)+relativedelta(months=-3)).date()
        for dat in query:
            if dat.date<currdate and dat.date>=threemonthreldate:
                threemonthdata.append(dat.coliform)
        change='N/A'
        if len(threemonthdata)!=0 and sum(threemonthdata)>0.0:
            change=str(round(((colicount-np.mean(threemonthdata))/np.mean(threemonthdata))*100.0,2))+"%"
        pdf.cell(250, 8, txt="Colifrom Percentage Change Compared To Mean of Last Three Months : "+change, ln=1)
        now=datetime.datetime.now()
        pdf.output("stats_"+str(now.year)+"_"+str(now.month)+"_"+str(now.day)+"_"+str(now.hour)+"_"+str(now.minute)+"_"+str(now.second)+".pdf")
        #cleanup
        filelist = glob(os.getcwd()+'\\data\\TempImages\\*')
        for f in filelist:
            os.remove(f)
        
def main():
    app = QApplication(sys.argv)
    form = Explorer()
    form.show()
    app.exec_()

if __name__ == '__main__':              # if we're running file directly and not importing it
    main()                              # run the main function


