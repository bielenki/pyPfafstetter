# -*- coding: utf-8 -*-


__author__ = 'Jannik Schilling'
__date__ = '2019-07-26'
__copyright__ = '(C) 2019 by Jannik Schilling'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import *
import processing
import numpy as np

class accumulation(QgsProcessingAlgorithm):
    

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return accumulation()

    def accumPath(self, parameters, context, feedback):
        '''
        source = self.parameterAsSource(
            parameters,
            self.INPUT_LAYER,
            context
        )
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        '''
        INPUT_LAYER = parameters['streams']
        INPUT_FIELD_CALC = parameters['area']
        INPUT_FIELD_ID = parameters['id']
        INPUT_FIELD_NEXT = 'tonode'
        INPUT_FIELD_PREV = 'fromnode'
        INPUT_CRS = parameters['crs']
        INPUT_WKT = parameters['wkt']
        OUTPUT = parameters['OUTPUT']
        
        '''loading the network'''
        waternet = INPUT_LAYER
        wnet_fields = waternet.fields()
        '''Counter for the progress bar'''
        total = waternet.featureCount()
        parts = 100/total 
        #QgsMessageLog.logMessage("total features in waternet:  " + str(total),'MyPlugin', Qgis.Info)
        '''names of fields for id,next segment, previous segment'''
        id_field = INPUT_FIELD_ID
        next_field = INPUT_FIELD_NEXT
        prev_field = INPUT_FIELD_PREV
        calc_field = INPUT_FIELD_CALC
        #QgsMessageLog.logMessage("names of field:  " + id_field + "  " + next_field +"  " + prev_field + "   "+ calc_field,'MyPlugin', Qgis.Info)
        '''field index for id,next segment, previous segment'''
        idxId = waternet.fields().indexFromName(id_field) 
        idxPrev = waternet.fields().indexFromName(prev_field)
        idxNext = waternet.fields().indexFromName(next_field)
        idxCalc = waternet.fields().indexFromName(calc_field)
        #QgsMessageLog.logMessage("index of field:  " + str(idxId) + "  " + str(idxPrev) +"  " + str(idxNext) + "   "+ str(idxCalc),'MyPlugin', Qgis.Info)

        '''load data from layer "waternet" '''
        feedback.setProgressText(self.tr("Loading network layer\n "))
        #for f in waternet.getFeatures():
        #    QgsMessageLog.logMessage(str(f.attribute(idxId)) +"  " + str(f.attribute(idxPrev)) + "   "+ str(f.attribute(idxNext)) + "   " + str(f.attribute(idxCalc)),'MyPlugin', Qgis.Info)
        Data = [[str(f.attribute(idxId)),str(f.attribute(idxPrev)),str(f.attribute(idxNext)),f.attribute(idxCalc)] for f in waternet.getFeatures()]
        DataArr = np.array(Data, dtype='object')
        DataArr[np.where(DataArr[:,3] == NULL),3]=0
        feedback.setProgressText(self.tr("Data loaded \n Calculating flow paths \n"))

        '''segments with numbers'''
        calc_column = np.copy(DataArr[:,3]) #deep copy of column to do calculations on
        calc_segm = np.where(calc_column > 0)[0].tolist() 
        DataArr[:,3] = 0 # set all to 0

        '''function to find next features in the net'''
        def nextFtsCalc (MARKER2):
            vtx_to = DataArr[np.where(DataArr[:,0] == MARKER2)[0].tolist(),2][0] # "to"-vertex of actual segment
            rows_to = np.where(DataArr[:,1] == vtx_to)[0].tolist() # find rows in DataArr with matching "from"-vertices to vtx_to
            return(rows_to)

        '''function to find flow path'''
        def FlowPath (Start_Row, fp_amount):
            MARKER=DataArr[Start_Row,0] #set MARKER to ID of the first segment
            Weg = [Start_Row]    
            i=0
            while i!=len(DataArr):
                next_rows = nextFtsCalc(MARKER)
                if len(next_rows) > 1: # deviding flow path
                    calc_column[StartRow] = 0
                    calc_column[next_rows] = calc_column[next_rows]+fp_amount/len(next_rows) # this can be changed to weightet separation later
                    out = [Weg, next_rows]
                    break
                if len(next_rows) == 1: # continuing flow path
                    Weg = Weg + next_rows
                    MARKER=DataArr[next_rows[0],0] # change MARKER to Id of next segment 
                if len(next_rows) == 0: # end point
                    out = [Weg]
                    break
                i=i+1
            return (out)

        total2 = len(calc_segm)
        while len(calc_segm) > 0:
            if feedback.isCanceled():
                break
            StartRow = calc_segm[0]
            amount = calc_column[StartRow] # amount to add to flow path
            calc_column[StartRow] = 0 #"delete" calculated amount from list (set 0)
            Fl_pth = FlowPath(StartRow, amount) # get flow path of StartRow 
            if len(Fl_pth)== 2:
                calc_segm = calc_segm + Fl_pth[1] # if flow path devides add new segments to calc_segm
            DataArr[Fl_pth[0],3] = DataArr[Fl_pth[0],3]+amount # Add the amount to the calculated flow path
            calc_segm = calc_segm[1:] # delete used segment
            calc_segm = list(set(calc_segm)) #delete duplicate values
            feedback.setProgress((1-(len(calc_segm)/total2))*100)

        '''add new field'''
        new_field_name = 'acc_down'
        #define new fields
        out_fields = QgsFields()
        #append fields
        for field in wnet_fields:
            out_fields.append(QgsField(field.name(), field.type()))
        out_fields.append(QgsField(new_field_name, QVariant.Double))


        '''sink definition'''
        dest_id = OUTPUT
        
        dest_id.startEditing()
        dest_id.dataProvider().addAttributes(out_fields)#inFields.toList())
        dest_id.commitChanges()

        '''create output / add features to sink'''
        feedback.setProgressText(self.tr("creating output \n"))
        features = waternet.getFeatures()
#        i=0
        featureList=[]
        for (i,feature) in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break
            # Add a feature in the sink
            outFt = QgsFeature()
            outFt.setGeometry(feature.geometry())
            outFt.setAttributes(feature.attributes())
            outFt.setAttributes(feature.attributes()+[DataArr[i,3]])
            featureList.append(outFt)
            #dest_id.addFeature(outFt, QgsFeatureSink.FastInsert)
            #dest_id.updateFeature(outFt)
            feedback.setProgress((i+1)*parts)
        dest_id.startEditing()
        dest_id.dataProvider().addFeatures(featureList)
        dest_id.commitChanges()
        return dest_id

        del nextFtsCalc
        del FlowPath
        del DataArr


        return {}
