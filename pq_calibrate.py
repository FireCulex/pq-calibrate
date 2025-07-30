import numpy as np
from scipy.interpolate import interp1d
import datetime
import math
import json

# --- SMPTE ST 2084 (PQ) EOTF Constants ---
M1 = 2610 / 16384.0
C1 = 3424 / 4096.0
C2 = 2413 / 4096.0 * 32.0
C3 = 2392 / 4096.0 * 32.0
M2 = 2523 / 4096.0 * 128.0

# --- Calculate PQ Nits Function ---
def calculate_pq_nits(pq_percentage_value: float) -> float:
    """
    Calculates the ideal PQ luminance in nits for a given PQ percentage value.
    This uses the SMPTE ST 2084 (PQ) EOTF with a 10,000 nit peak.
    Uses globally defined constants M1, M2, C1, C2, C3.
    """
    if not (0.0 <= pq_percentage_value <= 100.0):
        raise ValueError("PQ percentage value must be between 0.0 and 100.0")
    
    normalized_pq_value = pq_percentage_value / 100.0

    N_pow_inv_m2 = normalized_pq_value**(1/M2)

    numerator = N_pow_inv_m2 - C1
    denominator = C2 - C3 * N_pow_inv_m2

    if denominator <= 0:
        return 0.0
    
    base = numerator / denominator
    if base < 0:
        return 0.0

    L_norm_10000 = base**(1/M1)
    nits = L_norm_10000 * 10000
    return nits

# --- LUT Generation Function (Modified for ArgyllCMS .cal format) ---

def generate_argy_cal_lut(lut_size: int, corrected_1d_curve: np.ndarray, title: str = "PQ Calibration LUT") -> str:
    """
    Generates an ArgyllCMS compatible .cal (or .lut) format 1D LUT string.
    """
    header = "CAL\n"
    header += f"DESCRIPTOR \"{title}\"\n"
    header += "ORIGINATOR \"Python_Gemini_Calibrator\"\n"
    created_time = datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S %Y")
    header += f"CREATED \"{created_time}\"\n"
    header += "DEVICE_CLASS \"DISPLAY\"\n"
    header += "COLOR_REP \"RGB\"\n"
    header += "TABLE_RGB_FROM_DISPLAY_PRIMARIES\n" # Added this line for ArgyllCMS if it's a display LUT
    header += "NUMBER_OF_FIELDS 4\n"
    header += "BEGIN_DATA_FORMAT\n"
    header += "RGB_I RGB_R RGB_G RGB_B\n"
    header += "END_DATA_FORMAT\n\n"
    header += f"NUMBER_OF_SETS {lut_size}\n"
    header += "BEGIN_DATA\n"
    lut_string = ""
    input_values = np.linspace(0, 1, lut_size)
    for i in range(lut_size):
        input_val = input_values[i]
        corrected_val = corrected_1d_curve[i]
        lut_string += f"{input_val:.14f}\t{corrected_val:.14f}\t{corrected_val:.14f}\t{corrected_val:.14f}\n"
    lut_string += "END_DATA\n"
    return header + lut_string

def calibrate_pq_to_lut( 
    peak_luminance: float,
    lut_size: int,
    filename_cal: str,
    measurements: list
):
    """
    Performs a PQ EOTF calibration and generates an ArgyllCMS .cal LUT file.
    This function *requires* 'measurements' to perform multi-point correction.
    All parameters must be provided by the caller, typically from a configuration file.
    """
    if not measurements: # This check is still good to ensure 'measurements' isn't empty or None unexpectedly
        raise ValueError("Measurements are required for calibration. Please provide a list of [PQ%, Measured Nits] tuples.")

    print(f"Target Peak Luminance (for overall context and LUT generation): {peak_luminance:.1f} nits")
    print(f"LUT Size: {lut_size} points (NUMBER_OF_SETS)")
    print(f"Output LUT File: {filename_cal}")

    lut_input_grid_points = np.linspace(0, 1, lut_size)
    corrected_output_code_values = np.linspace(0, 1, lut_size)

    input_code_points_user = []
    measured_Y_points_user = []
    target_Y_points_for_lut_and_print = []

    for p_white, m_Y in measurements:
        norm_code = p_white / 100.0
        input_code_points_user.append(norm_code)
        measured_Y_points_user.append(m_Y)
        
        ideal_target_nits_at_10000_peak = calculate_pq_nits(p_white)
        
        clamped_target_nits = np.clip(ideal_target_nits_at_10000_peak, 0.0, peak_luminance)
        target_Y_points_for_lut_and_print.append(clamped_target_nits)

    input_code_points_user = np.array(input_code_points_user)
    measured_Y_points_user = np.array(measured_Y_points_user)
    target_Y_points_for_lut_and_print = np.array(target_Y_points_for_lut_and_print)

    # Sort measurements by input code to ensure proper interpolation
    sort_indices = np.argsort(input_code_points_user)
    input_code_points_user = input_code_points_user[sort_indices]
    measured_Y_points_user = measured_Y_points_user[sort_indices]
    target_Y_points_for_lut_and_print = target_Y_points_for_lut_and_print[sort_indices]

    print(f"{'Input %':<10} | {'Measured Y (nits)':<20} | {'Calculated Target Y (nits)':<28}")
    print(f"{'-'*10}-+-{'-'*20}-+-{'-'*28}")
    for i in range(len(input_code_points_user)):
        original_input_percentage = measurements[sort_indices[i]][0]
        print(f"{original_input_percentage:<10.1f} | {measured_Y_points_user[i]:<20.3f} | {target_Y_points_for_lut_and_print[i]:<28.3f}")
    print(f"{'-'*10}-+-{'-'*20}-+-{'-'*28}\n")

    # Create interpolation functions
    # inverse_measured_response_interp maps measured nits back to input code values
    inverse_measured_response_interp = interp1d(
        np.unique(measured_Y_points_user), # Use unique values for x to avoid interp1d errors
        input_code_points_user[np.unique(measured_Y_points_user, return_index=True)[1]],
        kind='slinear',
        bounds_error=False,
        fill_value=(input_code_points_user[0], input_code_points_user[-1])
    )

    # target_luminance_curve_interp maps input code values to desired target nits
    target_luminance_curve_interp = interp1d(
        input_code_points_user,
        target_Y_points_for_lut_and_print,
        kind='slinear',
        bounds_error=False,
        fill_value=(target_Y_points_for_lut_and_print[0], target_Y_points_for_lut_and_print[-1])
    )

    # Apply correction to the LUT input grid
    for i, lut_input_code in enumerate(lut_input_grid_points):
        desired_target_nits = target_luminance_curve_interp(lut_input_code).item()
        raw_corrected_output_code = inverse_measured_response_interp(desired_target_nits).item()
        corrected_output_code_values[i] = np.clip(raw_corrected_output_code, 0.0, 1.0)
        
    corrected_output_code_values = np.clip(corrected_output_code_values, 0.0, 1.0)

    lut_content = generate_argy_cal_lut(lut_size, corrected_output_code_values, title="HCFR PQ Calibration")

    try:
        with open(filename_cal, 'w') as f:
            f.write(lut_content)
        print(f"\nSuccessfully generated and saved LUT to: {filename_cal}")
    except IOError as e:
        print(f"Error saving file {filename_cal}: {e}")

# Example Usage:
if __name__ == "__main__":
    
    config_file_path = "eotf_measurements.json"
    
    try:
        with open(config_file_path, 'r') as f:
            config_data = json.load(f)
        print(f"Successfully loaded configuration and measurements from {config_file_path}")

        json_peak_luminance = config_data.get("peak_luminance")
        json_lut_size = config_data.get("lut_size")
        json_filename_cal = config_data.get("filename_cal")
        json_measurements = config_data.get("measurements")

        # Basic validation for required parameters (still good practice)
        if json_peak_luminance is None:
            raise ValueError(f"'{config_file_path}' is missing the required 'peak_luminance' key.")
        if json_lut_size is None:
            raise ValueError(f"'{config_file_path}' is missing the required 'lut_size' key.")
        if json_filename_cal is None:
            raise ValueError(f"'{config_file_path}' is missing the required 'filename_cal' key.")
        if json_measurements is None:
            raise ValueError(f"'{config_file_path}' is missing the required 'measurements' key.")

        # Call the calibration function with parameters from the JSON file
        calibrate_pq_to_lut( # Changed function name here
            peak_luminance=json_peak_luminance,
            lut_size=json_lut_size,
            filename_cal=json_filename_cal,
            measurements=json_measurements
        )

    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file_path}' not found.")
        print("Please ensure 'eotf_measurements.json' is in the same directory as the script.")
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from '{config_file_path}'. Check file format: {e}")
    except ValueError as e:
        print(f"Configuration error in '{config_file_path}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred while reading configuration: {e}")