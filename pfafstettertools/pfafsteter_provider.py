# -*- coding: utf-8 -*-


__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider
from .networkConstructor import networkConst
from .accum import accumulation
from .upDist import upDist


class NetworkToolsProvider(QgsProcessingProvider):
    """Main class"""
    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(networkConst())
        self.addAlgorithm(accumulation())
        self.addAlgorithm(upDist())
        

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'wnt'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.
        """
        return self.tr('Network')

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QgsProcessingProvider.icon(self)

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Water Network Tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
