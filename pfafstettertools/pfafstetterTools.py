# -*- coding: utf-8 -*-
"""
/***************************************************************************
 pfafsteter
                                 A QGIS plugin
 Codificação de bacias hidrográficas pelo método de Otto Pfafsteter
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-02-12
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Claudio Bielenki Jr
        email                : bielenki@ufscar.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QPushButton, QLabel, QDialogButtonBox
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox, QgsFeaturePickerWidget
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel, QgsProcessingContext, QgsProcessingFeedback, QgsProcessingParameters, QgsVectorFileWriter, QgsExpression, QgsSpatialIndex, QgsField
from qgis.core import QgsVectorLayer, QgsProject, QgsProcessingUtils, QgsMessageLog, Qgis, QgsFeatureRequest, QgsProcessingAlgorithm, QgsProcessingFeatureSource, QgsWkbTypes, QgsRectangle
from qgis.core import edit
import sys

import qgis.utils
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .pfafsteterTools_dialog import pfafsteterDialog

from .incremental_dialog import incrementalDialog
import os.path
from .pfafsteter_provider import NetworkToolsProvider
from .networkConstructor import networkConst
from .accum import accumulation
from .upDist import upDist
import os, sys, math, time, operator
import pandas as pd
import pysal as ps
import numpy as np
import fiona
import geopandas as gpd
from shutil import copyfile

# Global lists
checked = []
tocheck = []
flipped = []

def COC (pfafstetter):
    global cocursodag
    cocursodag = ""
    i=-1
    for cont in range(len(pfafstetter)):
        if int(pfafstetter[i]) % 2 == 0:
            cocursodag = pfafstetter[:len(pfafstetter)-cont]
            break
        i=i-1
    return (cocursodag)




def query_jusante (cobac, lista):
    Ncobacia = "Pfaf"
    Ncocurso = "cocurso"
    query = ""
    q = ""
    lista.sort()
    for x in lista:
        query = """\"{0}\" = '{1}' OR """.format(Ncocurso,x) + q
        q=query
    q = q[0:-4]
    q = "(" + q + ")"
    q = """\"{0}\" <= '{1}' and """.format(Ncobacia,cobac) + q
    query=unicode(q)
    return query

def dbf2DF(dbfile): # Parametro arquivo dbf
         '''
            a funcao le o arquivo dbf e converte em Pandas Data Frame
            mantendo o nome dos atributos
         '''
         db = ps.open(dbfile) #Pysal para ler o DBF
         d = {col: db.by_col(col) for col in db.header} #Converte o dbf em dicionario
         pandasDF = pd.DataFrame(d) #Converte para Pandas DF
         db.close()   # fecha o arquivo dbf
         return pandasDF   # Retorna um data frame

def appendcol2dbf(dbf_in, dbf_out, col_name, col_spec, col_data,
                  replace=False):

    '''
        a funcao adiciona a um dbf um campo com os respectivos dados
    '''
    # abre o dbf original e cria um novo com o novo campo
    db= ps.open(dbf_in)
    db_new = ps.open(dbf_out, 'w')
    db_new.header = db.header
    db_new.header.append(col_name)
    db_new.field_spec = db.field_spec
    db_new.field_spec.append(col_spec)
    # adiciona ao dbf o dado original e o novo dado
    item = 0
    for rec in db:
        rec_new = rec
        rec_new.append(col_data[item])
        db_new.write(rec_new)
        item += 1
    # fecha os arquivos
    db_new.close()
    db.close()

    if replace is True:
        os.remove(dbf_in)
        os.rename(dbf_out, dbf_in)

def classif_rios(df):
    '''
        a funcao classifica uma selecao de trechos para o primeiro nivel
        a partir da identificacao do canal principal
    '''
    delta=0.9*df.Perimetro.min()
    teste=2
    max_acum=df.acc_down.max()
    FNODE=df.loc[df['acc_down']==max_acum]['fromnode'].max()
    principal=pd.DataFrame(columns=['area','id','dist','tnodeP','pfafstetter'])
    tributario=pd.DataFrame(columns=['area','id','dist','fnodeT','pfafstetter'])
    ind=df.loc[df['fromnode']==FNODE].index[0]
    x=df.loc[ind,'acc_down'].max()
    y=df.loc[ind,'rid'].max()
    z=df.loc[ind,'upDist'].max()-df.loc[ind,'Perimetro'].max()
    principal = principal.append({'area': x, 'id': y, 'dist': z, 'pfafstetter':'1'},ignore_index=True)

    i=0
    while teste==2:
        i=i+1
        teste=df.query('tonode=='+str(FNODE)).tonode.count()
        Maior_area=df.query('tonode=='+str(FNODE)).acc_down.max()
        Menor_area=df.query('tonode=='+str(FNODE)).acc_down.min()
        fnodeT=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).tonode.max()
        tnodeP=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).fromnode.max()
        ID_maior=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).rid.max()
        ID_menor=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Menor_area)).rid.max()
        dist_maior=(df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).upDist.max())-(df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).Perimetro.max())
        dist_menor=(df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Menor_area)).upDist.max())-(df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Menor_area)).Perimetro.max())
        principal = principal.append({'area': Maior_area, 'id': ID_maior, 'dist': dist_maior,'tnodeP': tnodeP,'pfafstetter': '999'},ignore_index=True)
        tributario = tributario.append({'area': Menor_area, 'id': ID_menor, 'dist': dist_menor,'fnodeT': fnodeT,'pfafstetter': '999'},ignore_index=True)
        FNODE=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).fromnode.max()
        if df.query('tonode=='+str(FNODE)).tonode.count() == 0 : break
    next
    copia=tributario.copy()
    copia=copia.sort_values('area',ascending=False)
    dados=pd.DataFrame(copia.reset_index(drop=True))
    if i<=3:
        areasSB=pd.DataFrame(dados.loc[0:i-1])
    else:
        areasSB=pd.DataFrame(dados.loc[0:3])
    areasSB=areasSB.sort_values('dist')
    Topfour=pd.DataFrame(areasSB.reset_index(drop=True))

    ultimo_interbac = str((Topfour.id.count()*2)+1)

    cont=1
    for rows in Topfour.pfafstetter:
        Topfour.loc[cont-1,'pfafstetter']=str(cont*2)
        cont=cont+1

    for index in Topfour.iterrows():
        distancia=(Topfour.loc[index[0],'dist'])-delta
        for index2, teste in principal.iterrows():
            if round(teste['dist'],3) < distancia and teste['pfafstetter']=='999' :
                #print (teste['dist'])
                principal.loc[index2,'pfafstetter'] =  str(int(Topfour.loc[index[0],'pfafstetter'])-1)

    for index4, teste in principal.iterrows():
        if teste['pfafstetter']=='999' :
            principal.loc[index4,'pfafstetter'] = ultimo_interbac

    if i<=3:
        trib=dados.loc[i+1:]
    else:
        trib=dados.loc[4:]

    trib=trib.sort_values('dist')
    tributario=pd.DataFrame(trib.reset_index(drop=True))
    tributario.columns=['area','id','dist','fnodeT','pfafstetter']


    for index in Topfour.iterrows():
        dist_teste=(Topfour.loc[index[0],'dist'])-delta
        for index6, teste3 in tributario.iterrows():
            if round(teste3['dist'],3) < dist_teste and teste3['pfafstetter']=='999':
                tributario.loc[index6,'pfafstetter']= str(int(Topfour.loc[index[0],'pfafstetter'])-1)
            elif teste3['pfafstetter']=='999':
                break

    for index8, teste in tributario.iterrows():
        if teste['pfafstetter']=='999' :
            tributario.loc[index8,'pfafstetter'] = ultimo_interbac

    Topfour.columns=['area','id','dist','fnodeT','pfafstetter']
    frames = [Topfour,principal,tributario]
    framesConcat=pd.concat(frames)
    df_join=df.join(framesConcat.set_index('id'), on='rid',how='outer')
    df_join.drop_duplicates(subset='rid',keep='first',inplace=True)
    desconectados=[df_join.loc[df_join['pfafstetter'].isnull()].rid, df_join.loc[df_join['pfafstetter'].isnull()].tonode, df_join.loc[df_join['pfafstetter'].isnull()].upDist]
    list_desc=list(np.array(desconectados))
    Tlist=np.transpose(list_desc)
    dfTlist=pd.DataFrame(Tlist)
    dfTlist.sort_values(2,ascending=True, inplace=True)
    Tlist=np.array(dfTlist)
    cont=0

    for rows in Tlist:
        valor = df_join.loc[df_join['fromnode'] == Tlist[cont][1]]['pfafstetter'].max()
        #df_join.set_value(df_join.loc[df_join['rid'] == Tlist[cont][0]]['pfafstetter'].index,'pfafstetter',str(int(valor)))
        df_join.at[df_join.loc[df_join['rid'] == Tlist[cont][0]]['pfafstetter'].index,'pfafstetter']=str(int(valor))
        cont=cont+1

    return (df_join)

def springs (df):
    Lfnode=list(df['fromnode'])
    Ltnode=list(df['tonode'])
    nasc=[item for item in Lfnode if item not in Ltnode]
    df_nasc=df[['rid','fromnode']]
    df_nasc['springs']=0
    for item in nasc:
        #df_nasc.set_value(df_nasc.loc[df_nasc['fromnode']==item].index,'springs',1)
        df_nasc.at[df_nasc.loc[df_nasc['fromnode']==item].index,'springs']=1
    return (df_nasc)


def canal_principal (df):
    max_acum=df.acc_down.max()
    FNODE=df.loc[df['acc_down']==max_acum]['fromnode'].max()
    teste=2
    canal=pd.DataFrame(columns=['area','id','tnodeP','canal'])
    ind=df.query('fromnode=='+str(FNODE)).index
    x=df.loc[ind,'acc_down'].max()
    y=df.loc[ind,'rid'].max()
    canal = canal.append({'area': x, 'id': y, 'canal':'1'},ignore_index=True)
    i=0
    while teste==2:
        i=i+1
        teste=df.query('tonode=='+str(FNODE)).tonode.count()
        Maior_area=df.query('tonode=='+str(FNODE)).acc_down.max()
        fnodeT=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).tonode.max()
        tnodeP=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).fromnode.max()
        ID_maior=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).rid.max()
        canal = canal.append({'area': Maior_area, 'id': ID_maior, 'tnodeP': tnodeP,'canal': 1},ignore_index=True)
        FNODE=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).fromnode.max()
        if df.query('tonode=='+str(FNODE)).tonode.count() == 0 : break
    canalP=df.join(canal.set_index('id'), on='rid',how='outer')
    return (canalP)




class pfafsteter:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        self.provider = None
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'pfafsteter_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        #self.menu = self.tr(u'&Pfafstetter Tools')


        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
    def initProcessing(self):

        self.provider = NetworkToolsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('pfafstetter', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=False,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent= None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.toolBar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action
    def hello(self):
        self.iface.messageBar().pushMessage(u'Welcome to Otto Pfafstetter Conding Tools', level=Qgis.Info, duration=3)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.toolBar = self.iface.addToolBar("Pfafstetter Tools")
        self.toolBar.setObjectName("pfafstetterTools")

        icon_path = ':/plugins/pfafstettertools/images/newacumula.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Pfafstetter Tool'),
            callback=self.hello,
            parent=self.iface.mainWindow())

        drainageLabel=QLabel(self.toolBar)
        drainageLabel.setText("Drainage Network: ")
        self.toolBar.addWidget(drainageLabel)

        self.drainageCombo = QgsMapLayerComboBox()
        self.fieldCombo = QgsFieldComboBox()


        self.drainageCombo.setFixedWidth(200)
        self.drainageCombo.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.toolBar.addWidget(self.drainageCombo)
        self.drainageCombo.setToolTip("Select the drainage network")

        self.toolBar.addSeparator()

        icon_path = ':/plugins/pfafstettertools/images/otto64.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Otto Pfafstetter Coding System'),
            callback=self.run,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/pfafstettertools/images/upstream.png'
        self.add_action(
            icon_path,
            text=self.tr(u'UpStream Tool'),
            callback=self.funUpStream,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/pfafstettertools/images/downstream.png'
        self.add_action(
            icon_path,
            text=self.tr(u'DownStream Tool'),
            callback=self.funDownStream,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/pfafstettertools/images/FlowAccumulation.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Stream Accumulation Tool'),
            callback=self.funAccum,
            parent=self.iface.mainWindow())


        self.fieldCombo.setFixedWidth(200)
        self.fieldCombo.setFilters(QgsFieldProxyModel.Numeric)
        self.toolBar.addWidget(self.fieldCombo)
        self.fieldCombo.setToolTip("Select the attribute to accumulation")

        layerField = self.drainageCombo.currentLayer()
        self.fieldCombo.setLayer(layerField)

        icon_path = ':/plugins/pfafstettertools/images/check.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Hydronet Check & Flip (by Jeronimo Carranza). \nSelect prior the outfall arcs in the active layer.'),
            callback=self.checkandflip,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/pfafstettertools/images/Incremental.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Incremental Area Tool'),
            callback=self.incremental,
            parent=self.iface.mainWindow())


        self.drainageCombo.layerChanged.connect(self.drainageChange)

        # will be set False in run()
        self.first_start = True

    def drainageChange(self):
        self.fieldCombo.setLayer(self.drainageCombo.currentLayer())
        self.iface.setActiveLayer(self.drainageCombo.currentLayer())


    def cbIDChange(self):
        self.dlg.cbFeatureOutlet.setDisplayExpression(self.dlg.cbID.currentField())

    def selectFeature(self):
        sLayer = self.drainageCombo.currentLayer()
        sLayer.removeSelection()
        sFeatureID = self.dlg.cbFeatureOutlet.feature().id()
        sLayer.select(sFeatureID)


        #return outletID

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        #del pfafsteterTools


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
        self.dlg = pfafsteterDialog()

        self.dlg.labelDN.setText(self.drainageCombo.currentLayer().name())

        self.dlg.pbCoding.button(QDialogButtonBox.Ok).setText("Coding")
        self.dlg.cbLenght.setFilters(QgsFieldProxyModel.Numeric)
        self.dlg.cbArea.setFilters(QgsFieldProxyModel.Numeric)
        self.dlg.cbLenght.setLayer(self.drainageCombo.currentLayer())
        self.dlg.cbArea.setLayer(self.drainageCombo.currentLayer())
        self.dlg.cbID.setFilters(QgsFieldProxyModel.Numeric)
        self.dlg.cbID.setLayer(self.drainageCombo.currentLayer())

        self.dlg.cbFeatureOutlet.setLayer(self.drainageCombo.currentLayer())
        self.dlg.cbFeatureOutlet.setDisplayExpression(self.dlg.cbID.currentField())
        self.dlg.cbID.fieldChanged.connect(self.cbIDChange)
        self.dlg.cbFeatureOutlet.featureChanged.connect(self.selectFeature)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            parameters={}
            streamLayer = self.drainageCombo.currentLayer()
            parameters['streams'] = streamLayer

            idField = self.dlg.cbID.currentField()
            parameters['id'] = idField

            lenghtField = self.dlg.cbLenght.currentField()
            parameters['lenght'] = lenghtField

            areaField = self.dlg.cbArea.currentField()
            parameters['area'] = areaField
            context = QgsProcessingContext()
            context.setProject(QgsProject.instance())
            feedback = QgsProcessingFeedback()

            results = networkConst.network(self, parameters, context, feedback)

            newNet = QgsProcessingUtils.mapLayerFromString(results['Network'], context)
            name = self.iface.activeLayer().name()
            newName = name + "_Cod1"
            path = self.iface.activeLayer().dataProvider().dataSourceUri()
            newPath1 = path.replace(name,newName)
            QgsVectorFileWriter.writeAsVectorFormat( newNet , newPath1, "UTF-8", self.iface.activeLayer().crs() , "ESRI Shapefile")

            newNetwork = QgsVectorLayer(newPath1, "Net", "ogr")

            activeLayer = self.iface.activeLayer()

            prov = activeLayer.dataProvider()
            idxOutlet = prov.fieldNameIndex(idField)

            selection = activeLayer.selectedFeatures()
            #iterate over selected features
            for feat in selection:
                outletID = feat.attributes()[idxOutlet]


            dataP = newNetwork.dataProvider()

            field_idx1 = dataP.fieldNameIndex('fromode')
            field_idx2 = dataP.fieldNameIndex('tonode')
            field_idx3 = dataP.fieldNameIndex('rid')

            outlet = int(0)
            expression1 = parameters['id']+"="+str(outletID)

            selection=newNetwork.getFeatures(QgsFeatureRequest().setFilterExpression(expression1))
            newNetwork.startEditing()
            for feat in selection:
                feat['fromnode'] = outletID
                newNetwork.updateFeature(feat)
                feat['tonode'] = outlet
                newNetwork.updateFeature(feat)
                feat['rid'] = outletID
                newNetwork.updateFeature(feat)
                #atributos = feat.attributes()
            newNetwork.commitChanges()
            #QgsMessageLog.logMessage("valores   " + str(atributos[field_idx1]) +"  "+ str(atributos[field_idx2]), 'MyPlugin', Qgis.Info)

            columnFields = ['fromnode','tonode', parameters['id'], parameters['lenght'], parameters['area'], 'rid', 'COBACIA']
            dataP = newNetwork.dataProvider()
            fieldsNet = dataP.fields()
            columnFieldsDrop = []
            for field in fieldsNet:
                if field.name() not in columnFields:
                    index = dataP.fieldNameIndex(field.name())
                    columnFieldsDrop.append(index)

            dataP.deleteAttributes(columnFieldsDrop)
            newNetwork.updateFields()

            parameters['streams'] = newNetwork
            CRS = activeLayer.crs().authid()
            WKBType = activeLayer.wkbType()
            temp = QgsVectorLayer("Linestring?crs=" + CRS, "Network2", "memory")
            parameters['OUTPUT'] = temp
            parameters['crs'] = CRS
            parameters['wkt'] = WKBType
            acc = accumulation.accumPath(self, parameters, context, feedback)
            parameters['streams'] = acc
            preNet = upDist.upDistCalc(self, parameters, context, feedback)

            name = self.iface.activeLayer().name()
            newName = name + "_Cod"
            path = self.iface.activeLayer().dataProvider().dataSourceUri()
            newPath = path.replace(name,newName)

            netCod = QgsVectorFileWriter.writeAsVectorFormat(preNet, newPath, "UTF-8", self.iface.activeLayer().crs() , "ESRI Shapefile")

            pfaf_inicial = self.dlg.leCodeI.text()

            rio = newPath.replace('shp','dbf')

            df= dbf2DF(rio) # conversao de dbf para o pandas data frame
            df.rename(columns = {lenghtField : 'Perimetro'}, inplace = True)


            df.sort_values('upDist',ascending=True, inplace=True)

            df_class1 = classif_rios(df)

            df['pfaf']=df_class1['pfafstetter']

            Todos_classificados=False

            while Todos_classificados==False:

                Duplicados=df['pfaf'].duplicated()
                if True in list(Duplicados):
                    for indexDuplicado, itemDuplicado in Duplicados.iteritems():
                        if itemDuplicado == True:
                            IndexDFpfaf=indexDuplicado
                            break
                    codpfaf=df.loc[IndexDFpfaf,'pfaf']
                    sel_df=df[df['pfaf']==codpfaf]
                    sel_df.sort_values('upDist',ascending=True, inplace=True)

                    df_ClassN = classif_rios(sel_df)
                    df_ClassN.sort_values('upDist',ascending=True, inplace=True)

                    for indexDFjoin, itemDFjoin in df_ClassN.iterrows():
                        var_rid = int(itemDFjoin.rid)
                        pfaf1 = itemDFjoin.pfafstetter
                        if type(pfaf1)==str:
                            pfaf2=df.loc[df['rid']==var_rid]['pfaf']
                            valor_pfaf = pfaf2.max()+pfaf1
                            #df.set_value(df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf',(valor_pfaf))
                            df.at[df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf']=valor_pfaf
                        if type(pfaf1)==float:
                            if math.isnan(pfaf1):
                                valor_pfaf=df.loc[df['fromnode']==var_rid]['pfaf'].max()
                                #df.set_value(df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf',(valor_pfaf))
                                df.at[df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf']=valor_pfaf
                                break
                            else:
                                pfaf2=df.loc[df['rid']==var_rid]['pfaf']
                                valor_pfaf = pfaf2.max()+pfaf1
                                #df.set_value(df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf',(valor_pfaf))
                                df.at[df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf']=valor_pfaf
                else:
                    Todos_classificados=True
                    break

            for indexRow, rows in df.iterrows():
                pfaf3=rows['pfaf']
                pfaf_fim=pfaf_inicial+pfaf3
                #df.set_value(indexRow,'pfaf',pfaf_fim)
                df.at[indexRow,'pfaf']=pfaf_fim

            canal = canal_principal(df)
            na = springs(df)

            df['cocurso']=''

            for indexRow, rows in df.iterrows():
                pfafs=rows['pfaf']
                cocurso= COC(pfafs)
                #df.set_value(indexRow,'cocurso',cocurso)
                df.at[indexRow,'cocurso']=cocurso

            dbf_in = rio
            dbf_out = rio.replace('.dbf','_copy.dbf')
            col_name = 'Pfaf'
            col_spec = ('C',15,0)
            db = ps.open(dbf_in)
            n = db.n_records
            col_data = df.loc[df['pfaf'].notnull()]['pfaf']
            db.close()
            appendcol2dbf(dbf_in,dbf_out,col_name,col_spec,col_data,replace=True)

            col_name = 'mainstreams'
            col_spec = ('C',1,0)
            db = ps.open(dbf_in)
            n = db.n_records
            col_data = canal['canal']
            db.close()
            appendcol2dbf(dbf_in,dbf_out,col_name,col_spec,col_data,replace=True)

            col_name = 'springs'
            col_spec = ('C',1,0)
            db = ps.open(dbf_in)
            n = db.n_records
            col_data = na['springs']
            db.close()
            appendcol2dbf(dbf_in,dbf_out,col_name,col_spec,col_data,replace=True)

            col_name = 'cocurso'
            col_spec = ('C',15,0)
            db = ps.open(dbf_in)
            n = db.n_records
            col_data = df['cocurso']
            db.close()
            appendcol2dbf(dbf_in,dbf_out,col_name,col_spec,col_data,replace=True)


            vlayer = QgsVectorLayer(newPath, "NetCode", "ogr")
            QgsProject.instance().addMapLayer(vlayer)

            del dataP
            del newNetwork


            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
    def funAccum(self):
            """Run method that performs all the real work"""

            if self.first_start == True:
                self.first_start = False
            activeLayer = self.iface.activeLayer()
            accumField = self.fieldCombo.currentField()

            coluna=accumField+"_Accum"
            dfp=gpd.read_file(activeLayer.source())
            dfp[coluna]=0
            for index, row in dfp.iterrows():
                cobac=row.Pfaf
                cocur=row.cocurso
                dfp_sel= dfp.loc[operator.and_(dfp.Pfaf>=cobac, dfp.cocurso.str.startswith(cocur))]
                soma = dfp_sel[accumField].sum()
                dfp.loc[index, coluna]= soma
                del dfp_sel

            output=activeLayer.source().replace(".shp","_Accum.shp")
            dfp.to_file(driver = 'ESRI Shapefile', filename = output)
            newlayer = QgsVectorLayer(output, "Accumulation" , "ogr")
            QgsProject.instance().addMapLayer(newlayer)

            pass


    def funUpStream(self):
            """Run method that performs all the real work"""

            if self.first_start == True:
                self.first_start = False
            activeLayer = self.iface.activeLayer()

            Nr_sel = activeLayer.selectedFeatureCount()
            if Nr_sel==0:
                self.iface.messageBar().pushMessage(u'It is necessary select one stream', level=Qgis.Info, duration=3)
            elif Nr_sel>1:
                self.iface.messageBar().pushMessage(u'It is necessary select just one stream', level=Qgis.Info, duration=3)
            elif Nr_sel==1:
                prov = activeLayer.dataProvider()
                idx = prov.fieldNameIndex("Pfaf")
                selection = activeLayer.selectedFeatures()
                #iterate over selected features
                for feat in selection:
                    cobacia_ini = feat.attributes()[idx]

                cocurso_ini=COC(cobacia_ini)
                NPfaf="Pfaf"
                Ncocurso="cocurso"
                activeLayer.removeSelection()

                query = """\"{0}\" >= '{1}' AND \"{2}\" LIKE '{3}%' """.format(NPfaf,cobacia_ini,Ncocurso, cocurso_ini)
                #exp = QgsExpression(unicode(query))
                activeLayer.selectByExpression(str(unicode(query)))
                self.iface.actionZoomToSelected().trigger()
            pass




    def funDownStream(self):
            """Run method that performs all the real work"""

            if self.first_start == True:
                self.first_start = False
            activeLayer = self.iface.activeLayer()

            Nr_sel = activeLayer.selectedFeatureCount()
            if Nr_sel==0:
                self.iface.messageBar().pushMessage(u'It is necessary select one stream', level=Qgis.Info, duration=3)
            elif Nr_sel>1:
                self.iface.messageBar().pushMessage(u'It is necessary select just one stream', level=Qgis.Info, duration=3)
            elif Nr_sel==1:
                prov = activeLayer.dataProvider()
                idx = prov.fieldNameIndex("Pfaf")
                selection = activeLayer.selectedFeatures()
                #iterate over selected features
                for feat in selection:
                    cobacia_ini = feat.attributes()[idx]
                cocurso_ini = COC(cobacia_ini)
                lista_cursos = COC_jusante(cobacia_ini)
                activeLayer.removeSelection()

                where_clause = QgsExpression("\"Pfaf\" <= '{}'".format(cobacia_ini))
                lista_cocursos=[]
                features = activeLayer.getFeatures(QgsFeatureRequest(where_clause))
                for feat in features:
                    cobacia = feat.attributes()[idx]
                    if COC(cobacia) in lista_cursos:
                        lista_cocursos.append(COC(cobacia))


                q=query_jusante(cobacia_ini,lista_cocursos)


                activeLayer.selectByExpression(str(q))
                self.iface.actionZoomToSelected().trigger()
            pass

    def checkandflip(self):
        """Run method that performs all the real work
        """
        layer = qgis.utils.iface.mapCanvas().currentLayer()

        if layer is None:
            qgis.utils.iface.messageBar().pushMessage(u"Hydronet Check and Flip ", u"No selected layer", level=Qgis.Critical)
            return

        if layer.geometryType() != QgsWkbTypes.LineGeometry:
            qgis.utils.iface.messageBar().pushMessage(u"Hydronet Check and Flip ", u"The selected layer is not a line layer", level=Qgis.Critical)
            return

        if layer.selectedFeatures() == []:
            qgis.utils.iface.messageBar().pushMessage(u"Hydronet Check and Flip ", u"No selected outfall arcs", level=Qgis.Critical)
            return

        """ Outfalls """
        outfalls = layer.selectedFeatures()

        """ Spatial index """
        index = QgsSpatialIndex(layer.getFeatures())

        global tocheck
        global checked
        global flipped

        """ Checking for each outfall """
        for feature in outfalls:
            checked.append(feature.id())
            self.checkarc(feature, index, layer)

        """ Check the updated list 'tocheck' """
        n = 0
        while(n <= len(layer) and len(tocheck) > 0):
            checked.append(tocheck[0])
            arc = [feat for feat in layer.getFeatures() if feat.id() == tocheck[0]]
            self.checkarc(arc[0], index, layer)
            tocheck = [x for x in set(tocheck) if x not in set(checked)]
            n = n + 1

        """ Finishing """
        QgsMessageLog.logMessage('Checked Arcs:: '+str(checked)[1:-1],'Hydronet Check and Flip', Qgis.Info)
        QgsMessageLog.logMessage('Flipped Arcs:: '+str(flipped)[1:-1],'Hydronet Check and Flip', Qgis.Info)
        qgis.utils.iface.mapCanvas().refresh()
        tocheck = []
        checked = []
        flipped = []


    def checkarc(self, arc, index, layer):
        global tocheck
        global checked
        global flipped
        uparcs_idx = self.arclist(arc, index, layer, 0)
        dwarcs_idx = self.arclist(arc, index, layer, -1)
        if (self.anyin(uparcs_idx, checked)):
            self.flip(arc, layer)
            tocheck.extend(dwarcs_idx)
            flipped.append(arc.id())
        else:
            tocheck.extend(uparcs_idx)


    def arclist(self, arc, index, layer, op):
        delta = 0.000001
        geom = arc.geometry()
        if geom.isMultipart():
            multi_geom = geom.asMultiPolyline()
            opnode = multi_geom[op][op]
        else:
            nodes = geom.asPolyline()
            opnode = nodes[op]
        opnode_rectangle = QgsRectangle(opnode.x()-delta, opnode.y()-delta, opnode.x()+delta, opnode.y()+delta)
        oparcs_idx = index.intersects(opnode_rectangle)
        oparcs_idx.remove(arc.id())
        return(oparcs_idx)


    def flip(self, arc, layer):
        layer.startEditing()
        layer.beginEditCommand( "Flipping" )
        geom = arc.geometry()
        if geom.isMultipart():
            multi = QgsMultiLineString()
            for line in geom.asGeometryCollection():
                multi.addGeometry(line.constGet().reversed())
            revgeom = QgsGeometry(multi)
            layer.changeGeometry(arc.id(),revgeom)
        else:
            revgeom = QgsGeometry(geom.constGet().reversed())
            layer.changeGeometry(arc.id(),revgeom)
        layer.endEditCommand()


    def anyin(self, xlist, ylist):
        for xi in xlist:
            if (xi in ylist):
                return(True)
                break
        return(False)

    def incrementalChange(self):
        self.dlg.attributeCB.setLayer(self.dlg.layerCB.currentLayer())
        self.dlg.codeCB.setLayer(self.dlg.layerCB.currentLayer())


    def incremental(self):
        if self.first_start == True:
            self.first_start = False
        self.dlg = incrementalDialog()

        self.dlg.layerCB.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.dlg.layerCB.setToolTip("Select the point features layer")

        self.dlg.attributeCB.setFilters(QgsFieldProxyModel.Numeric)
        self.dlg.codeCB.setFilters(QgsFieldProxyModel.String)
        self.dlg.attributeCB.setLayer(self.dlg.layerCB.currentLayer())
        self.dlg.codeCB.setLayer(self.dlg.layerCB.currentLayer())

        self.dlg.layerCB.layerChanged.connect(self.incrementalChange)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        if result:
            layer = self.dlg.layerCB.currentLayer()
            layerSource = self.dlg.layerCB.currentLayer().source()
            attributeField = self.dlg.attributeCB.currentField()
            codeField = self.dlg.codeCB.currentField()
            gdfUHE = gpd.read_file(layerSource)
            gdfUHE['COB'] = ''
            gdfUHE['COCURSO'] = ''
            for ind, r in gdfUHE.iterrows():
                cobacia = r[codeField]
                gdfUHE.at[ind, 'COB'] = str(cobacia)
                cocurso = COC(cobacia)
                gdfUHE.at[ind, 'COCURSO'] = str(cocurso)
            #print(gdfUHE['COB'])
            #print(gdfUHE['COCURSO'])

            gdfUHECopy = gdfUHE.copy()
            gdfUHE['incremental']=''
            for index, row in gdfUHECopy.iterrows():
                cob = row['COB']
                coc = row['COCURSO']
                area = row[attributeField]
                gdf = gdfUHECopy[(gdfUHECopy['COB']>cob) & (gdfUHECopy['COCURSO'].astype(str).str.startswith(coc))]
                if gdf.empty:
                    gdfUHE.loc[gdfUHE.COB == cob, 'incremental'] = area
                if len(gdf.index)==1:
                    area2 = gdf.iloc[0]['Area']
                    gdfUHE.loc[gdfUHE.COB == cob, 'incremental'] = area - area2
                if len(gdf.index)>1:
                    aux = gdf.copy()
                    for index2, row2 in aux.iterrows():
                        cob2 = row2['COB']
                        coc2 = row2['COCURSO']
                        aux2 = aux[(aux['COB']>cob2) & (aux['COCURSO'].astype(str).str.startswith(coc2))]
                        cond = gdf['COB'].isin(aux2['COB'])
                        gdf.drop(gdf[cond].index, inplace = True)
                    area3 = gdf[attributeField].sum()
                    gdfUHE.loc[gdfUHE.COB == cob, 'incremental'] = area - area3

                layerProvider=layer.dataProvider()
                layerProvider.addAttributes([QgsField("attrInc",QVariant.Double, '',20,6)])
                layer.updateFields()
                attID = layer.fieldNameIndex("attrInc")

            with edit(layer):

                features=layer.getFeatures()
                #layer.startEditing()
                #print (gdfUHE['incremental'])
                for f in features:
                    cobacia2 = f[codeField]
                    #print(cobacia2)
                    incrementalArea = gdfUHE.loc[gdfUHE['COB']==cobacia2, 'incremental'].values[0]
                    #print(incrementalArea)
                    fid = f.id()

                    attrValue = {attID:incrementalArea}

                    layerProvider.changeAttributeValues({fid : attrValue})
                    #f['attrInc'] = incrementalArea
                    #print(f['attrInc'])
                    #layer.updateFeature(f)
                #layer.commitChanges()
            QgsProject.instance().reloadAllLayers()
            pass
