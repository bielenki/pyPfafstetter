"""
Cláudio Bielenki Jr
17/02/2022

Model exported as python.
Name : Network
Group : Drainage
With QGIS : 31603
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingUtils
import processing


class networkConst(QgsProcessingAlgorithm):

    
    def network(self, parameters, context, model_feedback):
        
        feedback = QgsProcessingMultiStepFeedback(9, model_feedback)
        results = {}
        outputs = {}

        # Extract specific vertices
        alg_params = {
            'INPUT': parameters['streams'],
            'VERTICES': '-1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['verticeEnd'] = processing.run('native:extractspecificvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Extract specific vertices
        alg_params = {
            'INPUT': parameters['streams'],
            'VERTICES': '0',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['verticeStart'] = processing.run('native:extractspecificvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Intersection
        alg_params = {
            'INPUT': outputs['verticeStart']['OUTPUT'],
            'INPUT_FIELDS': [''],
            'OVERLAY': outputs['verticeEnd']['OUTPUT'],
            'OVERLAY_FIELDS': [''],
            'OVERLAY_FIELDS_PREFIX': 'From_',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['intersectionVertices'] = processing.run('native:intersection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Add field to attributes table
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'tonode',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,
            'INPUT': outputs['intersectionVertices']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddField1'] = processing.run('native:addfieldtoattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Add field to attributes table
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'fromnode',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,
            'INPUT': outputs['AddField1']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddField2'] = processing.run('native:addfieldtoattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}
        id2 = "From_" + parameters['id']
        id3 = 'IF ("'+id2+'" IS NULL, 0 , "'+  parameters['id']+'")'
        id4 = 'IF ("'+id2+'" IS NULL, 1 , "'+  id2+'")'
        
        # Field calculator
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'tonode',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': id3,
            'INPUT': outputs['AddField2']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FieldCalculator1'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}
        
        # Field calculator
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'fromnode',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': id4,
            'INPUT': outputs['FieldCalculator1']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FieldCalculator2'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}
        
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'rid',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,
            'INPUT': outputs['FieldCalculator2']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
         }
        outputs['AddField3'] = processing.run('native:addfieldtoattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)   
        
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'rid',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': id4,
            'INPUT': outputs['AddField3']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FieldCalculator3'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # Join attributes by field value
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': parameters['id'],
            'FIELDS_TO_COPY': [''],
            'FIELD_2': id2,
            'INPUT': parameters['streams'],
            'INPUT_2': outputs['FieldCalculator3']['OUTPUT'],
            'METHOD': 1,
            'PREFIX': '',
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        outputs['JoinAttributesByFieldValue'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        results['Network'] = outputs['JoinAttributesByFieldValue']['OUTPUT']
        return results
    