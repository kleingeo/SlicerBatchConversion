from __future__ import absolute_import, division, \
    print_function  # Makes moving python2 to python3 much easier and ensures that nasty bugs involving integer division don't creep in
import os
import unittest

import pandas as pd
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


class LinkMRandCT(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Find the linking between the MR and CT files"
        parent.categories = ["Transform MR to CT"]
        parent.dependencies = []
        parent.contributors = ["Geoff Klein (None)"]
        parent.helpText = """
    This module is for converting MR scans to CT space with CT reg files.
    """
        self.parent.helpText += self.getDefaultModuleDocumentationLink()


class LinkMRandCTWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        # self.developerMode = True
        ScriptedLoadableModuleWidget.setup(self)

        font = qt.QFont()
        font.setBold(True)

        self.applyTransformButton = qt.QPushButton('Build Table')
        self.applyTransformButton.setFont(font)
        self.applyTransformButton.toolTip = 'BuildTable'
        self.applyTransformButton.enabled = True

        # Segmentation button connections
        self.applyTransformButton.connect('clicked(bool)', self.onTransformButton)

        self.layout.addWidget(self.applyTransformButton)

    def onTransformButton(self):
        main()


def main():
    slicer.mrmlScene.Clear(0)

    # # Parse command-line arguments
    # parser = argparse.ArgumentParser(description="Batch Structure Set Conversion")
    # parser.add_argument("-i", "--input-folder", dest="input_folder", metavar="PATH",
    #                     default="-", required=False,
    #                     help="Folder of input DICOM study (or database path to use existing)")
    # parser.add_argument("-r", "--ref-dicom-folder", dest="ref_dicom_folder", metavar="PATH",
    #                     default="", required=False,
    #                     help="Folder containing reference anatomy DICOM image series, if stored outside the input study")
    # parser.add_argument("-u", "--use-ref-image", dest="use_ref_image",
    #                     default=False, required=False, action='store_true',
    #                     help="Use anatomy image as reference when converting structure set to labelmap")
    # parser.add_argument("-x", "--exist-db", dest="exist_db",
    #                     default=False, required=False, action='store_true',
    #                     help="Process an existing database")
    # parser.add_argument("-m", "--export-images", dest="export_images",
    #                     default=True, required=False, action='store_true',
    #                     help="Export image data with labelmaps")
    # parser.add_argument("-o", "--output-folder", dest="output_folder", metavar="PATH",
    #                     default=".",
    #                     help="Folder for output labelmaps")
    #
    # args = parser.parse_args()

    # args.input_folder = 'W:/incomingOdette'

    exist_db = 'D:/SlicerModules/OdetteDicom_hold'
    # args.exist_db = 'C:/Users/gakle/Documents/SlicerDICOMDatabase'

    output_folder = 'C:/OdetteDicomProcessed'


    output_folder = output_folder.replace('\\', '/')


    full_df = pd.DataFrame(columns=['mrn',
                                    'ct_study_id', 'ct_study_uid', 'ct_series_uid',
                                    'mr_study_id', 'mr_study_uid', 'mr_series_uid', 'mr_series_number',
                                    'reg_series_uid', 'reg_instanceUID', 'reg_matrix'])

    DICOMUtils.openDatabase(exist_db)


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

        MR_series_uid_list = []

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

                    reg_transform = reg[0x0070, 0x0308][1][0x0070, 0x0309][0][0x0070, 0x030a][0][0x3006, 0x00c6].value

                    reg_dict_hold = {'reg_sop': reg_sopInstanceUID_0,
                                     'transform_number': 0,
                                     'seriesInstanceUID': seriesInstanceUID,
                                     'studyID': reg_study_ID,
                                     'reg_instance_uid': reg_instanceUID,
                                     'reg_transform': reg_transform}

                    reg_sop_list.append(reg_dict_hold)

                    reg_dict_hold = {'reg_sop': reg_sopInstanceUID_1,
                                     'transform_number': 1,
                                     'seriesInstanceUID': seriesInstanceUID,
                                     'studyID': reg_study_ID,
                                     'reg_instance_uid': reg_instanceUID,
                                     'reg_transform': reg_transform}

                    reg_sop_list.append(reg_dict_hold)


            elif (series_modality == 'MR'.lower()) or (series_modality == 'MRI'.lower()):
                MR_series_uid_list.append(seriesInstanceUID)

            elif series_modality == 'CT'.lower():
                CT_list.append(seriesInstanceUID)

        for mr_series_uid in MR_series_uid_list:

            last_values_MR = mr_series_uid.split('.')[-1]
            found_match = False

            for reg_dict in reg_sop_list:

                if found_match == True:
                    continue

                reg_sop = reg_dict['reg_sop']
                reg_transform_number = reg_dict['transform_number']
                reg_series_uid = reg_dict['seriesInstanceUID']
                reg_study_ID = reg_dict['studyID']

                reg_transform = reg_dict['reg_transform']

                reg_instanceUID = reg_dict['reg_instance_uid']

                last_values_reg = reg_sop.split('.')[-1]

                found_ct_for_pair = False
                ct_pair_series = None
                ct_study_uid = None

                mr_study_id = db_main.fieldForStudy('StudyID', db_main.studyForSeries(mr_series_uid))
                mr_seres_number = db_main.fieldForSeries('SeriesNumber', mr_series_uid)
                mr_study_uid = db_main.fieldForStudy('StudyInstanceUID', db_main.studyForSeries(mr_series_uid))

                if last_values_MR == last_values_reg:

                    for ct_series in CT_list:
                        ct_study_id = db_main.fieldForStudy('StudyID', db_main.studyForSeries(ct_series))
                        ct_study_uid = db_main.fieldForStudy('StudyInstanceUID', db_main.studyForSeries(ct_series))

                        if ct_study_id == reg_study_ID:
                            found_ct_for_pair = True
                            ct_pair_series = ct_series

                            continue

                    # matching_dict = {'mr_series': MR, 'transform_series': reg_uid,
                    #                  'transform_number': reg_transform_number,
                    #                  'studyID': reg_study_ID, 'ct_series': ct_pair_series,
                    #                  'reg_instanceUID': reg_instanceUID}

                    transform = slicer.util.getFirstNodeByName('SpatialRegistration')


                    matching_dict = {'mrn': patientID,

                                     'ct_study_id': reg_study_ID,
                                     'ct_series_uid': ct_pair_series,
                                     'ct_study_uid': ct_study_uid,

                                     'mr_study_id': mr_study_id,
                                     'mr_series_number': mr_seres_number,
                                     'mr_study_uid': mr_study_uid,
                                     'mr_series_uid': mr_series_uid,

                                     'reg_series_uid': reg_series_uid,
                                     'reg_instanceUID': reg_instanceUID,
                                     'reg_matrix': reg_transform}

                    full_df = full_df.append(matching_dict, ignore_index=True)

                    patientID_dict_matching_trans_mr[patientID].append(matching_dict)

                    found_match = True
                    continue

            if found_match == False:
                mr_series_number = db_main.fieldForSeries('SeriesNumber', mr_series_uid)
                mr_study_number = db_main.fieldForStudy('StudyID', db_main.studyForSeries(mr_series_uid))

                missing_mr_dict = {'SeriesNumber': mr_series_number, 'StudyID': mr_study_number}

                patient_ID_missing[patientID].append(missing_mr_dict)

                patient_all_mr_matches = False

        if patient_all_mr_matches == True:
            patient_ID_missing.pop(patientID)

            a = 1

    try:
        full_df.to_csv(os.path.dirname(__file__) + '/matching_df.csv', index=False)
    except:
        a = 1
