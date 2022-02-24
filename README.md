# pyPfafstetter
A new tool implemented with pyqgis to coding streams by Pfafstetter Method


**pyPfafstetterTools
A QGIS Plugin Toolbar to streams coding by Pfafstetter Method

 

Drainage Network ComboBox 

![bar1](https://github.com/bielenki/pyPfafstetter/blob/master/Fig/bar1.png?raw=true)
 
From this combobox, select the layer of the drainage network on which the toolbar tasks will be executed.
Button for encoding by Otto Pfafstetter
 
 
From this button you can access the Pfafstetter Tools Dialog Box to setup de inputs for encoding script.
 
The Otto Pfafstetter Coding script performs the coding of the drainage network sections. When executing the tool, the fields [Pfaf], [Mainstreams], [Springs] and [cocurso] are added to the attribute table.

Button upStream selection tool
  
 
From this button, and with a selected feature, the tool selects all the features of the layer that are upstream.
 
Button downStream selection tool
 
 
From this button, and with a selected feature, the tool selects all the features of the layer that are downstream, ie the way to the outfall.
 


Button accumulation tool
 
 
It accumulates a given attribute from upstream to downstream, adding a new layer to the project that is a copy of the drainage network layer added to a field in the attribute table that is the accumulated value of the attribute selected from the Attribute combobox. The added field receives the name of the selected field plus the suffix “_Accum”.
Attribute ComboBox 
 
From this combobox select the attribute table field that you want to accumulate with the accumulation function.

