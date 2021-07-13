import glob
import numpy as np
import pydicom

from skimage.draw import polygon

def get_study_from_rt(rt):
    """Parses RTSTRUCT metadata to return referenced CT study instance.
    
    Args:
        rt (pydicom rtstruct data): RTSTRUCT object containing metadata
                                    and contour information.
        
    Returns:
        Referenced CT study instance for RTSTRUCT

    """
    res = rt[0x3006, 0x10][0][0x3006, 0x12][0][0x08,0x1155][:].split('.') # reference study instance
    
    res[3] = res[3][:-1]
    res = '.'.join(res)
    return res


def get_series_from_rt(rt):
    """Parses RTSTRUCT metadata to return references CT series instance.
    
    Args:
        rt (pydicom rtstruct data): RTSTRUCT object containing metadata
                                    and contour information.
        
    Returns:
        Referenced CT series instance for RTSTRUCT
    
    """
    res = rt[0x3006, 0x10][0][0x3006, 0x12][0][0x3006,0x14][0][0x20,0x0e][:].split('.') # reference series instance
    
    res[3] = res[3][:-1]
    res = '.'.join(res)
    return res


def load_rtstruct(root, row):
    """Loads RTSTRUCT pydicom data.
    
    Args:
        root (pathlib.PosixPath): Root directory of patient dcm files.
        row (pandas Series): A row from the master dataframe to access
                             the path of the MR dicom directory.

    Returns:
        RTSTRUCT pydicom data.
    
    """
    path = (f"{root}/fullerkj/{row['parent']}/{row['pid']}/"
            f"{row['year']}/{row['study']}/{row['series']}/{row['modality']}")
    path = glob.glob(f'{path}/*')
    assert len(path) == 1
    rtstruct = pydicom.dcmread(path[0])
    return rtstruct


def process_rtstruct(structure):
    """Retrieve annotations from RTSTRUCT file.
    
    Args:
        structure: RTSTRUCT pydicom data.
        
    Returns:
        A list of contours stored in the file containing number, names,
        and contour coordinates.
    """
    try:
        contours = []
        for i in range(len(structure.ROIContourSequence)):
            contour = {'number': structure.ROIContourSequence[i].ReferencedROINumber,
                       'name': structure.StructureSetROISequence[i].ROIName}

            assert contour['number'] == structure.StructureSetROISequence[i].ROINumber
            contour['contours'] = [s.ContourData for s in structure.ROIContourSequence[i].ContourSequence]
            contours.append(contour)

        return contours
    except:
        return []
    
    
def convert_rtstruct_to_mask(contours, shape, slices):
    """Retrieve annotations from RTSTRUCT file.
    
    Args:
        structure: RTSTRUCT pydicom data.
        
    Returns:
        A list of contours stored in the file containing number, names,
        and contour coordinates.
    """
    z = [np.around(s.ImagePositionPatient[2], 1) for s in slices]
    pos_r = slices[0].ImagePositionPatient[1]
    spacing_r = slices[0].PixelSpacing[1]
    pos_c = slices[0].ImagePositionPatient[0]
    spacing_c = slices[0].PixelSpacing[0]
    
    label_map = np.zeros(shape, dtype=np.float32)
    for con in contours:
        num = int(con['number']) # add dict to map contour to label map
        for c in con['contours']:
            nodes = np.array(c).reshape((-1, 3))
            assert np.amax(np.abs(np.diff(nodes[:, 2]))) == 0
            z_index = z.index(np.around(nodes[0, 2], 1))
            r = (nodes[:, 1] - pos_r) / spacing_r
            c = (nodes[:, 0] - pos_c) / spacing_c
            rr, cc = polygon(r, c)
            label_map[z_index, rr, cc] = num

    return label_map



