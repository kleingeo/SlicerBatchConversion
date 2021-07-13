import os
import nibabel as nib


def get_mask(root, row, df):
    rt = load_rtstruct(root, row)

    ct_slices = get_ct_from_rtstruct(root, rt, df)
    ct = process_ct(ct_slices)

    patient_position = get_ct_patient_position(ct_slices)
    slice_thickness = get_ct_slice_thickness(ct_slices)
    pixel_spacing = get_ct_pixel_spacing(ct_slices)

    contours = process_rtstruct(rt)
    contours = [c for c in contours if c['name'].lower() in contour_type]
    
    if contours:
        mask = convert_rtstruct_to_mask(contours, ct.shape, ct_slices)
        return mask
    return 'bad'

def get_save_location(root, row):
    location = (f"{root}/evandros/processedOdette/"
                f"{row['pid']}/{row['year']}/{row['study']}/{row['series']}/"
                f"{row['modality']}/")

    return location

def save_mask(row, mask):
    location = get_save_location(root, row)
    Path(f'{location}').mkdir(parents=True, exist_ok=True)
    filename = os.path.join(location, f'{contour_type}.nii.gz')
       
    if not os.path.isfile(filename):
        img = nib.Nifti1Image(mask, np.eye(4))  # Save axis for data (just identity)
        nib.save(img, filename)  
    else:
        print('File exists')

def save_metadata(row, df):
    location = get_save_location(root, row)
    
    rt = load_rtstruct(root, row)
    
    ct_slices = get_ct_from_rtstruct(root, rt, df)
    
    patient_position = get_ct_patient_position(ct_slices)
    slice_thickness = get_ct_slice_thickness(ct_slices)
    pixel_spacing = get_ct_pixel_spacing(ct_slices)
    
    pid = get_ct_patient_id(ct_slices)
    study = get_study_from_rt(rt)
    series = get_series_from_rt(rt)
    
    metadata_path = os.path.join(location, 'metadata.txt')

    if not os.path.exists(metadata_path):
        with open(metadata_path, "w") as text_file:
            text_file.write("Patient ID: " + str(pid) + "\n")
            text_file.write("Study Instance UID: " + str(study) + "\n")
            text_file.write("Series Instance UID: " + str(series) + "\n")
            text_file.write("Slice Thickness: " + str(slice_thickness) + "\n")
            text_file.write("Slice Pixel Spacing: " + str(pixel_spacing) + "\n")
            text_file.write("Patient Position: " + str(patient_position) + "\n")