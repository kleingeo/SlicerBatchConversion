# SlicerBatchConversion

To run either script, the folder containing the files must be added to the modules path in Slicer. 

---
---

[`TransformMR2CT.py`](TransformMR2CT.py)

Slicer tools for converting Odette files.

TransformMR2CT applies the registration files to the MR files
so they are in CT space. In the code modify paths for existing Slicer 3D DICOM database adn the output directory.
Easiest to run with the paths hardcoded and best using an existing database created from Slicer 3D. 

To run script, in Slicer, after putting in the correct paths, the module can be found in Slicer by looking for 
`TransformMR2CT` and selecting the `ApplyTransform` button. 

---
---

[`BatchStructureSetConversionSeg.py`](BatchStructureSetConversionSeg.py)

BatchStructureSetConversion extracts the GTV, CTV and PTV for RTSTRUCT
dicom files. This script requires SlicerRT module. Similar to the other, it is best to hard-code the paths for an 
existing Slicer 3D DICOM database (same as above). 

This script is much slower than the transform one above. To ensure proper functionality it may be best to run this with
a smaller test database of maybe 5 to 10 patients. 

To run script, in Slicer, after putting in the correct paths, the module can be found in Slicer by looking for 
`BatchStructureSetConversionSeg` and selecting the `ExtractSegmentations` button. 

