# -*- coding: utf-8 -*-


__author__ = 'Cláudio Bielenki Júnior'
__date__ = '2022-02-19'
__copyright__ = '(C) 2022 by Cláudio Bielenki Jr'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import *
import processing
import numpy as np

class upDist(QgsProcessingAlgorithm):
    

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return upDist()

    def upDistCalc(self, parameters, context, feedback):
        
        INPUT_LAYER = parameters['streams']
        INPUT_Lenght = parameters['lenght']
   
        OUTPUT = parameters['OUTPUT']
        
        '''loading the network'''
        waternet = INPUT_LAYER
        layer_provider=waternet.dataProvider()
        layer_provider.addAttributes([QgsField("upDist",QVariant.Double)])
        waternet.updateFields()
        
        
        
        calc_field = INPUT_Lenght
        
        '''field index for id,next segment, previous segment'''
        idxId = waternet.fields().indexFromName('rid') 
        idxTo = waternet.fields().indexFromName('tonode')
        idxCalc = waternet.fields().indexFromName(calc_field)
        idxUp = waternet.fields().indexFromName("upDist")
        waternet.startEditing()
        features = waternet.getFeatures()
        
        for feat in features:
            
            idTo = feat.attributes()[idxTo]
            featID = feat.attributes()[idxId]
            #QgsMessageLog.logMessage("teste: id: "+str(featID)+"  tonode "+str(idTo),'MyPlugin', Qgis.Info)
            upDist = 0
            if idTo == 0: 
                upDist = feat.attributes()[idxCalc]            
            if idTo != 0:
                while idTo != 0:
                    idTo = waternet.getFeature(featID).attribute(idxTo)
                    dist = waternet.getFeature(featID).attribute(idxCalc)
                    upDist += dist
                    featID = idTo
                
            waternet.changeAttributeValue(feat.id(), idxUp, upDist)
            #QgsMessageLog.logMessage(str(upDist),'MyPlugin', Qgis.Info)
        waternet.commitChanges()
        
        
        
        
        
        
        return waternet

        
        return {}
