import glob
import numpy as np
import pydicom

from .rtstruct_utilities import get_study_from_rt, get_series_from_rt


def load_ct(root, row):
    """Loads CT pydicom data and creates SliceThickness metadata for processing.
    
    Args:
        root (pathlib.PosixPath): Root directory of patient dcm files.
        row (pandas Series): A row from the master dataframe to access
                             the path of the MR dicom directory.

    Returns:
        A list of CT pydicom data.
    
    """
    path = (f"{root}/fullerkj/{row['parent']}/{row['pid']}/"
            f"{row['year']}/{row['study']}/{row['series']}/{row['modality']}")
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


def get_ct_patient_id(slices):
    """Parses first CT slice of dicom files and returns patient ID.
    
    Args:
        slices: A list of CT pydicom data.

    Returns:
        A string of the patient ID.
        
    """
    return slices[0].PatientID

def get_ct_patient_position(slices):
    """Parses first CT slice of dicom files and returns patient position.
        
    Args:
        slices: A list of CT pydicom data.

    Returns:
        The x, y, and x coordinates of the upper left hand corner
        (center of the first voxel transmitted) of the image, in mm
        
    """
    patient_position = list(slices[0].ImagePositionPatient)
    patient_position = [float(p) for p in patient_position]
    patient_position = patient_position[::-1] # used to change (x,y,z)=>(z,y,x)
    return patient_position

def get_ct_slice_thickness(slices):
    """Parses first CT slice of dicom files and returns slice thickness.
    
    Args:
        slices: A list of CT pydicom data.

    Returns:
        A float of the CT slice thickness.
        
    """    
    slice_thickness = float(slices[0].SliceThickness)
    return slice_thickness


def get_ct_pixel_spacing(slices):
    """Parses first CT slice of dicom files and returns pixel spacing.
    
    Args:
        slices: A list of CT pydicom data.

    Returns:
        A list of floats of the CT pixel spacing in (z, y, x) format.
        
    """
    xy_spacing = list(slices[0].PixelSpacing)
    xy_spacing = [float(d) for d in xy_spacing]
    yx_spacing = xy_spacing[::-1]
    slice_thickness = [float(slices[0].SliceThickness)]
    pixel_spacing = slice_thickness + yx_spacing
    return pixel_spacing


def get_ct_from_rtstruct(root, rt, df):
    """Retrieves CT given rtstruct and dataframe table.
    
    Args:
        root (pathlib.PosixPath): Root directory of patient dcm files.
        rt (pydicom rtstruct data): RTSTRUCT object containing metadata
                                    and contour information.
        df (pandas DataFrame): Dataframe table containing all patient ids,
                               studies, series for referencing.

    Returns:
        A list of CT pydicom data.

    """
    study = get_study_from_rt(rt)
    series = get_series_from_rt(rt)
    row = df[(df['study']==study) & (df['series']==series)].squeeze()
    ct_slices = load_ct(root, row)
    return ct_slices


def process_ct(slices):
    """Processes CT dicom pixel array data to numpy array.
    
    Args:
        slices (list): List of pydicom data slices contained in original dicom files.

    Returns:
        A numpy array of the CT scan in HU.

    """
    image = np.stack([s.pixel_array for s in slices])
    # Convert to int16 (from sometimes int16), 
    # should be possible as values should always be low enough (<32k)
    image = image.astype(np.int16)

    # Set outside-of-scan pixels to 0
    # The intercept is usually -1024, so air is approximately 0
    image[image == -2000] = 0
    
    # Convert to Hounsfield units (HU)
    for slice_number in range(len(slices)):
        
        intercept = slices[slice_number].RescaleIntercept
        slope = slices[slice_number].RescaleSlope
        
        if slope != 1:
            image[slice_number] = slope * image[slice_number].astype(np.float64)
            image[slice_number] = image[slice_number].astype(np.int16)
            
        image[slice_number] += np.int16(intercept)
    
    return np.array(image, dtype=np.int16)

