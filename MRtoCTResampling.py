import os
import numpy
import SimpleITK as sitk


def resample_mr_to_ct(mr_img, ct_img):

    resample = sitk.ResampleImageFilter()

    resample.SetInterpolator(sitk.sitkLinear)
    resample.SetReferenceImage(ct_img)
    affine = sitk.AffineTransform(3)

    resample.SetTransform(affine)

    mr_resampled = resample.Execute(mr_img)

    return mr_resampled



if __name__ == '__main__':


    ct_img = sitk.ReadImage('D:/SpineSegmentation/VerSe2020/32277/4 Unnamed Series.nii.gz')

    mr_img = sitk.ReadImage('D:/SpineSegmentation/VerSe2020/32277/9 T8-T10 Ax 3D T1 FSPGR.nii.gz')

    mr_resampled = resample_mr_to_ct(mr_img, ct_img)

    sitk.WriteImage(mr_resampled, r'D:\SpineSegmentation\VerSe2020\32277/fuck_you.nii.gz')

