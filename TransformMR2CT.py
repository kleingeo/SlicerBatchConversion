from __future__ import absolute_import, division, \
    print_function  # Makes moving python2 to python3 much easier and ensures that nasty bugs involving integer division don't creep in
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import argparse
import sys
# import logging
from DICOMLib import DICOMUtils
import DICOMLib
import copy
import pydicom
import numpy as np


class TransformMR2CT(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Transform MR to CT Space"
        parent.categories = ["Transform MR to CT"]
        parent.dependencies = []
        parent.contributors = ["Geoff Klein (None)"]
        parent.helpText = """
    This module is for converting MR scans to CT space with CT reg files.
    """
        self.parent.helpText += self.getDefaultModuleDocumentationLink()


class TransformMR2CTWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        # self.developerMode = True
        ScriptedLoadableModuleWidget.setup(self)

        font = qt.QFont()
        font.setBold(True)

        self.applyTransformButton = qt.QPushButton('Apply Transform')
        self.applyTransformButton.setFont(font)
        self.applyTransformButton.toolTip = 'ApplyTransform'
        self.applyTransformButton.enabled = True

        # Segmentation button connections
        self.applyTransformButton.connect('clicked(bool)', self.onTransformButton)

        self.layout.addWidget(self.applyTransformButton)

    def onTransformButton(self):
        main()


def main():
    slicer.mrmlScene.Clear(0)

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

    # args.input_folder = 'W:/incomingOdette'

    args.exist_db = 'D:/SlicerModules/OdetteDicom_hold'
    # args.exist_db = 'C:/Users/gakle/Documents/SlicerDICOMDatabase'

    args.output_folder = 'C:/OdetteDicomProcessed'

    # Convert to python path style
    # input_folder = args.input_folder.replace('\\', '/')
    # ref_dicom_folder = args.ref_dicom_folder.replace('\\', '/')
    output_folder = args.output_folder.replace('\\', '/')

    # use_ref_image = args.use_ref_image
    exist_db = args.exist_db
    # export_images = args.export_images

    DICOMUtils.openDatabase(exist_db)

    # if exist_db:
    #   DICOMUtils.openDatabase(exist_db)
    # else:
    #   if os.path.isdir(ref_dicom_folder):
    #     DICOMUtils.openTemporaryDatabase()
    #     DICOMUtils.importDicom(ref_dicom_folder)
    #
    #   # logging.info("Import DICOM data from " + input_folder)
    #   DICOMUtils.openTemporaryDatabase()
    #   DICOMUtils.importDicom(input_folder)

    db_main = slicer.dicomDatabase

    patientID_dict = {}
    studyID_dict = {}

    patientID_dict_all_series = {}

    for patient_idx, patient in enumerate(db_main.patients()):
        patientID = db_main.fieldForPatient('PatientID', patient)
        if patientID not in patientID_dict.keys():
            patientID_dict[patientID] = None
            studyID_dict = {}

        if patientID not in patientID_dict_all_series.keys():
            patientID_dict_all_series[patientID] = []

        for studyInstanceUID in db_main.studiesForPatient(patient):
            studyID = db_main.fieldForStudy('StudyID', studyInstanceUID)

            if studyID not in studyID_dict.keys():
                studyID_dict[studyID] = []

            for seriesInstanceUID in db_main.seriesForStudy(studyInstanceUID):

                series_modality = db_main.fieldForSeries('Modality', seriesInstanceUID).lower()
                if (series_modality == 'RTPLAN'.lower()) or (series_modality == 'RTDOSE'.lower()):
                    continue

                studyID_dict[studyID].append(seriesInstanceUID)
                patientID_dict_all_series[patientID].append(seriesInstanceUID)

        patientID_dict[patientID] = studyID_dict

    # Extract transform IDs

    patientID_dict_matching_trans_mr = {}

    patient_ID_missing = {}

    for patientID in patientID_dict_all_series.keys():

        patientID_dict_matching_trans_mr[patientID] = []
        patient_ID_missing[patientID] = []

        patient_all_mr_matches = True

        patient_REG_list = []

        MR_list = []

        CT_list = []

        reg_sop_list = []

        for seriesInstanceUID in patientID_dict_all_series[patientID]:
            series_modality = db_main.fieldForSeries('Modality', seriesInstanceUID).lower()

            if series_modality == 'REG'.lower():
                patient_REG_list.append(seriesInstanceUID)

                # get sopInstanceUID from transfrom

                reg_file_list = db_main.filesForSeries(seriesInstanceUID)

                for reg_file in reg_file_list:
                    reg = pydicom.read_file(reg_file)

                    reg_sopInstanceUID_0 = reg[0x0008, 0x1115][0][0x0020, 0x000e].value
                    reg_sopInstanceUID_1 = reg[0x0008, 0x1115][1][0x0020, 0x000e].value

                    reg_instanceUID = reg[0x0008, 0x0018].value

                    reg_study_ID = reg[0x0020, 0x0010].value

                    reg_dict_hold = {'reg_sop': reg_sopInstanceUID_0,
                                     'transform_number': 0,
                                     'seriesInstanceUID': seriesInstanceUID,
                                     'studyID': reg_study_ID,
                                     'reg_instance_uid': reg_instanceUID}

                    reg_sop_list.append(reg_dict_hold)

                    reg_dict_hold = {'reg_sop': reg_sopInstanceUID_1,
                                     'transform_number': 1,
                                     'seriesInstanceUID': seriesInstanceUID,
                                     'studyID': reg_study_ID,
                                     'reg_instance_uid': reg_instanceUID}

                    reg_sop_list.append(reg_dict_hold)


            elif (series_modality == 'MR'.lower()) or (series_modality == 'MRI'.lower()):
                MR_list.append(seriesInstanceUID)

            elif series_modality == 'CT'.lower():
                CT_list.append(seriesInstanceUID)

        for MR in MR_list:

            last_values_MR = MR.split('.')[-1]
            found_match = False

            for reg_dict in reg_sop_list:

                reg_sop = reg_dict['reg_sop']
                reg_transform_number = reg_dict['transform_number']
                reg_uid = reg_dict['seriesInstanceUID']
                reg_study_ID = reg_dict['studyID']

                reg_instanceUID = reg_dict['reg_instance_uid']

                last_values_reg = reg_sop.split('.')[-1]

                found_ct_for_pair = False
                ct_pair_series = None

                if last_values_MR == last_values_reg:

                    for ct_series in CT_list:
                        ct_study_id = db_main.fieldForStudy('StudyID', db_main.studyForSeries(ct_series))

                        if ct_study_id == reg_study_ID:
                            found_ct_for_pair = True
                            ct_pair_series = ct_series

                            continue

                    matching_dict = {'mr_series': MR, 'transform_series': reg_uid,
                                     'transform_number': reg_transform_number,
                                     'studyID': reg_study_ID, 'ct_series': ct_pair_series,
                                     'reg_instanceUID': reg_instanceUID}

                    patientID_dict_matching_trans_mr[patientID].append(matching_dict)

                    found_match = True
                    continue

            if found_match == False:
                mr_series_number = db_main.fieldForSeries('SeriesNumber', MR)
                mr_study_number = db_main.fieldForStudy('StudyID', db_main.studyForSeries(MR))

                missing_mr_dict = {'SeriesNumber': mr_series_number, 'StudyID': mr_study_number}

                patient_ID_missing[patientID].append(missing_mr_dict)

                patient_all_mr_matches = False

        if patient_all_mr_matches == True:
            patient_ID_missing.pop(patientID)

            a = 1

    # print(patientID_dict_matching_trans_mr.keys())
    for patientID in patientID_dict_matching_trans_mr.keys():
        for matching_dict in patientID_dict_matching_trans_mr[patientID]:

            slicer.mrmlScene.Clear(0)  # clear the scene

            mr_series = matching_dict['mr_series']
            reg_uid = matching_dict['transform_series']
            reg_transform_number = matching_dict['transform_number']
            reg_study_id = matching_dict['studyID']

            ct_series = matching_dict['ct_series']

            reg_instanceUID = matching_dict['reg_instanceUID']

            output_dir = os.path.join(output_folder, patientID, reg_study_id)
            if not os.access(output_dir, os.F_OK):
                os.makedirs(output_dir)

            DICOMLib.loadByInstanceUID(reg_instanceUID)

            DICOMLib.loadSeriesByUID([mr_series])

            seq_collect_node = slicer.mrmlScene.GetNodesByName('Sequence')

            for num_seq in range(seq_collect_node.GetNumberOfItems()):
                slicer.mrmlScene.RemoveNode(seq_collect_node.GetItemAsObject(num_seq))

            mr = slicer.util.getNode('vtkMRMLScalarVolumeNode*')

            direction_matrix_vtk = vtk.vtkMatrix4x4()

            mr.GetIJKToRASDirectionMatrix(direction_matrix_vtk)

            direction_matrix = slicer.util.arrayFromVTKMatrix(direction_matrix_vtk)

            mr_origin = mr.GetOrigin()

            mr_spacing = mr.GetSpacing()
            mr_spacing_direction = mr.GetSpacing() * np.sign(direction_matrix[(0, 1, 2), (0, 1, 2)])

            mr_dimensions = mr.GetImageData().GetDimensions()

            bbox_extent = np.array(mr_origin) + np.array(mr_spacing_direction) * (np.array(mr_dimensions) - 1)

            image_extent = np.matmul(direction_matrix[:3, :3],
                                     np.array(mr_spacing) * (np.array(mr_dimensions) - 1)) + mr_origin

            mr_translation = (bbox_extent - image_extent) / 2

            mr_lin_transform = np.eye(4)

            mr_lin_transform[:3, -1] = mr_translation

            mr_lin_transform_vtk = slicer.util.vtkMatrixFromArray(mr_lin_transform)

            translation_transform = slicer.vtkMRMLLinearTransformNode()
            translation_transform.SetMatrixTransformToParent(mr_lin_transform_vtk)

            slicer.mrmlScene.AddNode(translation_transform)

            mr.SetAndObserveTransformNodeID(translation_transform.GetID())
            mr.HardenTransform()


            # transform = slicer.mrmlScene.GetNodesByName('1: SpatialReg [1]_SpatialRegistration').GetItemAsObject(0)

            transform = slicer.util.getFirstNodeByName('SpatialRegistration')

            mr.SetAndObserveTransformNodeID(transform.GetID())

            mr.HardenTransform()

            sv_nodes = slicer.util.getNodes('vtkMRMLScalarVolumeNode*')

            for imageNode in sv_nodes.values():
                # Clean up file name and set path
                fileName = imageNode.GetName() + '.nii.gz'
                table = str.maketrans(dict.fromkeys('!?:;'))
                fileName = fileName.translate(table)
                filePath = output_dir + '/' + fileName

                success = slicer.util.saveNode(imageNode, filePath)

            slicer.mrmlScene.Clear(0)  # clear the scene

            ct_series = matching_dict['ct_series']

            if ct_series is not None:
                DICOMLib.loadSeriesByUID([ct_series])

                ct_nodes = slicer.util.getNodes('vtkMRMLScalarVolumeNode*')

                for imageNode in ct_nodes.values():
                    # Clean up file name and set path
                    fileName = imageNode.GetName() + '.nii.gz'
                    table = str.maketrans(dict.fromkeys('!?:;'))
                    fileName = fileName.translate(table)
                    filePath = output_dir + '/' + fileName

            success = slicer.util.saveNode(imageNode, filePath)


if __name__ == "__main__":
    main()
