from __future__ import absolute_import, division, print_function # Makes moving python2 to python3 much easier and ensures that nasty bugs involving integer division don't creep in
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import argparse
import sys
import logging
from DICOMLib import DICOMUtils
import DICOMLib
import copy

# ------------------------------------------------------------------------------
# BatchStructureSetConversion
#   Convert structures in structure set to labelmaps and save them to disk
#
class BatchStructureSetConversionSeg(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Batch Structure Set Conversion"
        parent.categories = ["Converting structure sets and extracting segmentations."]
        parent.dependencies = ["DicomRtImportExport", "Segmentations"]
        parent.contributors = ["Csaba Pinter (Queen's)"]
        parent.helpText = """
    This is a module for converting DICOM structure set to labelmaps and saving them to disk.
    """
        self.parent = parent

        # Add this test to the SelfTest module's list for discovery when the module
        # is created.  Since this module may be discovered before SelfTests itself,
        # create the list if it doesn't already exist.
        try:
            slicer.selfTests
        except AttributeError:
            slicer.selfTests = {}
        slicer.selfTests['BatchStructureSetConversionSeg'] = self.runTest

    def runTest(self, msec=100, **kwargs):
        tester = BatchStructureSetConversionSegTest()
        tester.runTest()


class BatchStructureSetConversionSegidget(ScriptedLoadableModuleWidget):
  def setup(self):
    # self.developerMode = True
    ScriptedLoadableModuleWidget.setup(self)

    font = qt.QFont()
    font.setBold(True)

    self.extractSegButton = qt.QPushButton('Extract Segmentations')
    self.extractSegButton.setFont(font)
    self.extractSegButton.toolTip = 'ExtractSegmentations'
    self.extractSegButton.enabled = True

    # Segmentation button connections
    self.extractSegButton.connect('clicked(bool)', self.onExtractButton)

    self.layout.addWidget(self.extractSegButton)

  def onExtractButton(self):
    main()



# ------------------------------------------------------------------------------
# BatchStructureSetConversionLogic
#
class BatchStructureSetConversionSegLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget
    """

    def __init__(self):
      ScriptedLoadableModuleLogic.__init__(self)

      self.dataDir = slicer.app.temporaryPath + '/BatchStructureSetConversionSeg'
      if not os.access(self.dataDir, os.F_OK):
        os.mkdir(self.dataDir)

    def LoadFirstPatientIntoSlicer(self, patientID_list):
      # Choose first patient from the patient list
      # patient = slicer.dicomDatabase.patients()[0]
      # DICOMUtils.loadPatientByUID(patient)

      patientID = patientID_list[0]
      DICOMUtils.loadPatientByPatientID(patientID)


    def ConvertStructureSetToLabelmap(self, use_ref_image, ref_image_node_id=None):
      import vtkSegmentationCorePython as vtkSegmentationCore

      labelmapsToSave = []

      # Get reference image volume node
      referenceVolume = None
      if ref_image_node_id is not None:
        try:
          referenceVolume = slicer.util.getNode(ref_image_node_id)
        except slicer.util.MRMLNodeNotFoundException:
          logging.error('Failed to get reference image with ID ' + str(ref_image_node_id) + '. Using image referenced by DICOM')

      # Get all segmentation nodes from the scene
      segmentationNodes = slicer.util.getNodes('vtkMRMLSegmentationNode*')

      for segmentationNode in segmentationNodes.values():

        num_segments = segmentationNode.GetSegmentation().GetNumberOfSegments()

        segment_id_list = []
        for segment_idx in range(num_segments + 1):
          segment_id_list.append(segmentationNode.GetSegmentation().GetNthSegmentID(segment_idx))


        for segment_id in segment_id_list:
          if ((segment_id.lower() == 'gtv') or (segment_id.lower() == 'ctv') or (segment_id.lower() == 'ptv')) is False:
            segmentationNode.RemoveSegment(segment_id)


      # for segmentationNode in segmentationNodes.values():
        logging.info('  Converting structure set ' + segmentationNode.GetName())
        # Set referenced volume as rasterization reference from DICOM if not explicitly specified
        if referenceVolume is None and use_ref_image == True:
          referenceVolume = slicer.vtkSlicerDicomRtImportExportModuleLogic.GetReferencedVolumeByDicomForSegmentation(
            segmentationNode)
        if referenceVolume is None and use_ref_image == True:
          logging.error('No reference volume found for segmentation ' + segmentationNode.GetName())
          continue

        # Perform conversion
        if not segmentationNode.CreateBinaryLabelmapRepresentation():
          logging.error('Failed to create binary labelmap representation for segmentation ' + segmentationNode.GetName())
          continue

        # Create labelmap volume nodes from binary labelmaps
        allSegmentIDs = vtk.vtkStringArray()
        segmentationNode.GetSegmentation().GetSegmentIDs(allSegmentIDs)
        for segmentIndex in range(allSegmentIDs.GetNumberOfValues()):
          segmentID = allSegmentIDs.GetValue(segmentIndex)

          # Create output labelmap volume
          labelmapNode = slicer.vtkMRMLLabelMapVolumeNode()
          slicer.mrmlScene.AddNode(labelmapNode)
          labelmapName = segmentationNode.GetName() + "_" + segmentID
          labelmapNode.SetName(labelmapName)

          # Export single segment to labelmap
          singleSegmentIDArray = vtk.vtkStringArray()
          singleSegmentIDArray.InsertNextValue(segmentID)
          if not slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(
              segmentationNode, singleSegmentIDArray, labelmapNode, referenceVolume):
            logging.error('Failed to create labelmap from segment ' + segmentID + ' in segmentation ' + segmentationNode.GetName())
            continue

          # Append volume to list
          labelmapsToSave.append(labelmapNode)

      return labelmapsToSave

    def SaveLabelmaps(self, labelmapsToSave, outputDir):
      for labelmapNode in labelmapsToSave:
        # Clean up file name and set path

        gtv_index = 0
        ctv_index = 0
        ptv_index = 0

        if 'gtv' in labelmapNode.GetName().lower():
          label_name = f'gtv_seg_{gtv_index}'
          gtv_index += 1
        elif 'ctv' in labelmapNode.GetName().lower():
          label_name = f'ctv_seg_{ctv_index}'
          ctv_index += 1
        elif 'ptv' in labelmapNode.GetName().lower():
          label_name = f'ptv_seg_{ptv_index}'
          ptv_index += 1
        else:
          label_name = labelmapNode.GetName().lower
        fileName = label_name + '.nii.gz'
        table = str.maketrans(dict.fromkeys('!?:;'))
        fileName = fileName.translate(table)
        filePath = outputDir + '/' + fileName
        logging.info('  Saving structure ' + labelmapNode.GetName() + '\n    to file ' + fileName)

        # Save to file
        success = slicer.util.saveNode(labelmapNode, filePath)
        if not success:
          logging.error('Failed to save labelmap: ' + filePath)

    def SaveImages(self, outputDir, node_key='vtkMRMLScalarVolumeNode*'):
      # Save all of the ScalarVolumes (or whatever is in node_key) to NRRD files
      sv_nodes = slicer.util.getNodes(node_key)
      logging.info("Save image volumes nodes to directory %s: %s" % (outputDir, ','.join(sv_nodes.keys())))
      for imageNode in sv_nodes.values():
        # Clean up file name and set path
        fileName = imageNode.GetName() + '.nii.gz'
        table = str.maketrans(dict.fromkeys('!?:;'))
        fileName = fileName.translate(table)
        filePath = outputDir + '/' + fileName
        logging.info('  Saving image ' + imageNode.GetName() + '\n    to file ' + fileName)

        # Save to file
        success = slicer.util.saveNode(imageNode, filePath)
        if not success:
          logging.error('Failed to save image volume: ' + filePath)


# ------------------------------------------------------------------------------
# BatchStructureSetConversionTest
#
class BatchStructureSetConversionSegTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

    self.delayMs = 700

    # TODO: Comment out - sample code for debugging by writing to file
    # logFile = open('d:/pyTestLog.txt', 'a')
    # logFile.write(repr(slicer.modules.BatchStructureSetConversionSeg) + '\n')
    # logFile.close()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()

    self.test_BatchStructureSetConversionSeg_FullTest1()

  def test_BatchStructureSetConversionSeg_FullTest1(self):
    # Create logic
    self.logic = BatchStructureSetConversionSegLogic()

    # Check for modules
    self.assertTrue(slicer.modules.dicomrtimportexport)
    self.assertTrue(slicer.modules.segmentations)

    self.TestSection_0_SetupPathsAndNames()
    # Open test database and empty it
    with DICOMUtils.TemporaryDICOMDatabase(self.dicomDatabaseDir) as self.db:
      self.TestSection_1_LoadDicomData()
      self.TestSection_2_ConvertStructureSetToLabelmap()
      self.TestSection_3_SaveLabelmaps()
    logging.info('Test finished')

  def TestSection_0_SetupPathsAndNames(self):
    if not os.access(self.logic.dataDir, os.F_OK):
      os.mkdir(self.logic.dataDir)
    self.dicomDataDir = self.logic.dataDir + '/TinyRtStudy'
    if not os.access(self.dicomDataDir, os.F_OK):
      os.mkdir(self.dicomDataDir)

    # Define variables
    self.dataDir = slicer.app.temporaryPath + '/BatchStructureSetConversionSeg'
    if not os.access(self.dataDir, os.F_OK):
        os.mkdir(self.dataDir)
    self.dicomDatabaseDir = self.dataDir + '/CtkDicomDatabase'
    self.dicomZipFileUrl = 'http://slicer.kitware.com/midas3/download/folder/2822/TinyRtStudy.zip'
    self.dicomZipFilePath = self.logic.dataDir + '/TinyRtStudy.zip'
    self.expectedNumOfFilesInDicomDataDir = 12
    self.db = None
    self.outputDir = self.logic.dataDir + '/Output'

  def TestSection_1_LoadDicomData(self):
    try:
      self.assertTrue( self.db.isOpen )
      self.assertEqual( slicer.dicomDatabase, self.db)

      # Download, unzip, import, and load data. Verify selected plugins and loaded nodes.
      selectedPlugins = { 'Scalar Volume':1, 'RT':2 }
      loadedNodes = { 'vtkMRMLScalarVolumeNode':3, \
                      'vtkMRMLSegmentationNode':1 }
      with DICOMUtils.LoadDICOMFilesToDatabase( \
          self.dicomZipFileUrl, self.dicomZipFilePath, \
          self.dicomDataDir, self.expectedNumOfFilesInDicomDataDir, \
          {}, loadedNodes) as success:
        self.assertTrue(success)

    except Exception as e:
      import traceback
      traceback.print_exc()
      self.delayDisplay('Test caused exception!\n' + str(e),self.delayMs*2)

  def TestSection_2_ConvertStructureSetToLabelmap(self):
    self.delayDisplay("Convert loaded structure set to labelmap", self.delayMs)
    qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))
    try:
      self.labelmapsToSave = self.logic.ConvertStructureSetToLabelmap(use_ref_image=True)
      self.assertTrue(len(self.labelmapsToSave) > 0)
    except Exception as e:
      import traceback
      traceback.print_exc()
      self.delayDisplay('Test caused exception!\n' + str(e), self.delayMs * 2)
    qt.QApplication.restoreOverrideCursor()

  def TestSection_3_SaveLabelmaps(self):
    self.delayDisplay("Save labelmaps to directory\n  %s" % (self.outputDir), self.delayMs)

    self.assertTrue(len(self.labelmapsToSave) > 0)
    qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))

    self.logic.SaveLabelmaps(self.labelmapsToSave, self.outputDir)

    self.delayDisplay('  Labelmaps saved to  %s' % (self.outputDir), self.delayMs)
    qt.QApplication.restoreOverrideCursor()


def main():
  try:
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Batch Structure Set Conversion")
    parser.add_argument("-i", "--input-folder", dest="input_folder", metavar="PATH",
                        default="-", required=False,
                        help="Folder of input DICOM study (or database path to use existing)")
    parser.add_argument("-r", "--ref-dicom-folder", dest="ref_dicom_folder", metavar="PATH",
                        default="", required=False,
                        help="Folder containing reference anatomy DICOM image series, if stored outside the input study")
    parser.add_argument("-u", "--use-ref-image", dest="use_ref_image",
                        default=False, required=False, action='store_true',
                        help="Use anatomy image as reference when converting structure set to labelmap")
    parser.add_argument("-x", "--exist-db", dest="exist_db",
                        default=False, required=False, action='store_true',
                        help="Process an existing database")
    parser.add_argument("-m", "--export-images", dest="export_images",
                        default=True, required=False, action='store_true',
                        help="Export image data with labelmaps")
    parser.add_argument("-o", "--output-folder", dest="output_folder", metavar="PATH",
                        default=".",
                        help="Folder for output labelmaps")

    args = parser.parse_args()

    # args.input_folder = 'W:/OdetteDICOMS/Misaligned/SHSC-2d7f594065d24c8634e94bb2e5fb74d5578112323880c25505/20150323/input_folder'
    # args.input_folder = 'W:/OdetteDICOMS/Misaligned/SHSC-2d7f594065d24c8634e94bb2e5fb74d5578112323880c25505/20150323/hold'
    # args.input_folder = 'W:/incomingOdette'
    # # args.exist_db = 'D:/SlicerModules/20200825_025958_TempDICOMDatabase'
    # args.exist_db = 'D:/SlicerModules/OdetteDicom'
    # args.output_folder = 'W:/Odette_output_folder_hold'

    args.input_folder = 'C:/OdetteDicoms'
    # args.exist_db = 'D:/SlicerModules/20200825_025958_TempDICOMDatabase'
    args.exist_db = 'C:/Users/gakle/Documents/SlicerDICOMDatabase'
    args.output_folder = 'C:/OdetteDicomProcessed_Seg'




    # Check required arguments
    if args.input_folder == "-":
      logging.warning('Please specify input DICOM study folder!')
    if args.output_folder == ".":
      logging.info('Current directory is selected as output folder (default). To change it, please specify --output-folder')

    # Convert to python path style
    input_folder = args.input_folder.replace('\\', '/')
    ref_dicom_folder = args.ref_dicom_folder.replace('\\', '/')
    output_folder = args.output_folder.replace('\\', '/')

    use_ref_image = args.use_ref_image
    exist_db = args.exist_db
    # export_images = args.export_images
    export_images = False

    # Perform batch conversion
    logic = BatchStructureSetConversionSegLogic()
    def save_rtslices(output_dir, use_ref_image, ref_image_node_id=None):
      # package the saving code into a subfunction
      logging.info("Convert loaded structure set to labelmap volumes")
      labelmaps = logic.ConvertStructureSetToLabelmap(use_ref_image, ref_image_node_id=None)

      logging.info("Save labelmaps to directory " + output_dir)
      logic.SaveLabelmaps(labelmaps, output_dir)
      if export_images:
        logic.SaveImages(output_dir)
      logging.info("DONE")

    if exist_db:
      logging.info('BatchStructureSet running in existing database mode')
      DICOMUtils.openDatabase(exist_db)
      # all_patients = slicer.dicomDatabase.patients()
      # logging.info('Must Process Patients %s' % len(all_patients))

    else:
      ref_image_node_id = None
      if os.path.isdir(ref_dicom_folder):
        # If reference DICOM folder is given and valid, then load that volume
        logging.info("Import reference anatomy DICOM data from " + ref_dicom_folder)
        DICOMUtils.openTemporaryDatabase()
        DICOMUtils.importDicom(ref_dicom_folder)

      logging.info("Import DICOM data from " + input_folder)
      DICOMUtils.openTemporaryDatabase()
      DICOMUtils.importDicom(input_folder)


    db_main = slicer.dicomDatabase

    # Remove all scans that are not CT or RTSTRUCT to reduce unnecessary info





    patientID_dict = {}
    studyID_dict = {}

    for patient_idx, patient in enumerate(db_main.patients()):
      patientID = db_main.fieldForPatient('PatientID', patient)
      if patientID not in patientID_dict.keys():
        patientID_dict[patientID] = None
        studyID_dict = {}

      for studyInstanceUID in db_main.studiesForPatient(patient):
        studyID = db_main.fieldForStudy('StudyID', studyInstanceUID)

        if studyID not in studyID_dict.keys():
          studyID_dict[studyID] = []

        for seriesInstanceUID in db_main.seriesForStudy(studyInstanceUID):
          studyID_dict[studyID].append(seriesInstanceUID)
      patientID_dict[patientID] = studyID_dict




    for patientID in patientID_dict.keys():
      for studyID in patientID_dict[patientID].keys():

        seriesInstanceUID_list = patientID_dict[patientID][studyID]

        slicer.mrmlScene.Clear(0)  # clear the scene

        DICOMLib.loadSeriesByUID(seriesInstanceUID_list)

        output_dir = os.path.join(output_folder, patientID, studyID)
        if not os.access(output_dir, os.F_OK):
          os.makedirs(output_dir)
        save_rtslices(output_dir, use_ref_image)



  except Exception as e:
      print(e)



if __name__ == "__main__":
  main()

