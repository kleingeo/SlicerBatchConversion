import os
import numpy
import SimpleITK as sitk


def resample_mr_to_ct(mr_img, ct_img):

    resample = sitk.ResampleImageFilter()

    resample.SetInterpolator(sitk.sitkLinear)
    resample.SetReferenceImage(ct_img)
    affine = sitk.AffineTransform(3)

    resample.SetTransform(affine)

    seg = resample.Execute(mr_img)

    return seg

