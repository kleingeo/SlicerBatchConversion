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


class AdjustMRVolume(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Adjust MR"
        parent.categories = ["Transform MR to CT"]
        parent.dependencies = []
        parent.contributors = ["Geoff Klein (None)"]
        parent.helpText = """
        Adjust MR with a linear transform
    """
        self.parent.helpText += self.getDefaultModuleDocumentationLink()


class AdjustMRVolumeWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        # self.developerMode = True
        ScriptedLoadableModuleWidget.setup(self)


        inputCollapsibleButton = ctk.ctkCollapsibleButton()
        inputCollapsibleButton.text = "Input Volumes"
        self.layout.addWidget(inputCollapsibleButton)

        inputFormLayout = qt.QFormLayout(inputCollapsibleButton)

        self.inputSelector = slicer.qMRMLNodeComboBox()
        self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputSelector.selectNodeUponCreation = True
        self.inputSelector.addEnabled = False
        self.inputSelector.removeEnabled = False
        self.inputSelector.noneEnabled = False
        self.inputSelector.showHidden = False
        self.inputSelector.showChildNodeTypes = False
        self.inputSelector.setMRMLScene( slicer.mrmlScene )
        self.inputSelector.setToolTip( "Select the CT spine volume." )
        inputFormLayout.addRow("Input Volume: ", self.inputSelector)

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
        logic = AdjustMRVolumeLogic()
        logic.run(self.inputSelector.currentNode())


class AdjustMRVolumeLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)


    def onClick(self):
        pass

    def run(self, mr):

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

        slicer.mrmlScene.RemoveNode(translation_transform)
