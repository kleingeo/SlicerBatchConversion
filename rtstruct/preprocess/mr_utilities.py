import glob
import numpy as np
import pydicom


def load_mr(root, row):
    """Loads MR pydicom data and creates SliceThickness metadata for processing.
    
    Args:
        root (pathlib.PosixPath): Root directory of patient dcm files.
        row (pandas Series): A row from the master dataframe to access
                             the path of the MR dicom directory.

    Returns:
        A list of MR pydicom data.
    
    """
    path = (f"{root}/fullerkj/{row['parent']}/{row['pid']}/"
            f"{row['year']}/{row['study_uid']}/{row['series_uid']}/{row['modality']}")
    path = glob.glob(f'{path}/*')
    
    slices = [pydicom.dcmread(p) for p in path]
    slices.sort(key = lambda x: float(x.ImagePositionPatient[2]))

    thickness_exists = True
    for s in slices:
        if not getattr(s, 'SliceThickness', None):
            thickness_exists = False
    
    # measure from patient position or slice location if it's not in metadata
    if not thickness_exists:
        if "ImagePositionPatient" in slices[0]:
            print(slices[0].SliceThickness)
            slices.sort(key = lambda x: float(x.ImagePositionPatient[2]))
            try:
                slice_thickness = np.abs(slices[0].ImagePositionPatient[2] - slices[1].ImagePositionPatient[2])
            except:
                slice_thickness = np.abs(slices[0].SliceLocation - slices[1].SliceLocation)

            for s in slices:
                s.SliceThickness = slice_thickness
        
    return slices

def process_mr(slices):
    """Processes MR dicom pixel array data to numpy array.
    
    Args:
        slices (list): List of pydicom data slices contained in original dicom files.

    Returns:
        A numpy array of the MR scan.

    """
    image = np.stack([s.pixel_array for s in slices])
    return image