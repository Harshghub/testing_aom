"""
Perform a single measurement. 

Usage:
    python single_measurement.py
"""
import argparse
import time as t
import datetime as dt
import dwfpy as dwf
from dwfpy.constants import AnalogInputCoupling, GlobalParameter, TriggerSource
import numpy as np
import json
from pathlib import Path
# from trap_tester.utils import R_SENSE, SENSE_MAG

"""-----------------------------------------------------------------------"""



# Scope channel settings
CHANNEL_RANGE = 10#0.5  # Volts (±5V range)

INPUT_IMPEDANCE = 1e6 # 1e6  # Input impedance in Ohms (1MΩ = high impedance, 50Ω = low impedance)

# Analog output settings
# OUTPUT_FREQUENCY = 0.1e6# 1 kHz modulation frequency
# OUTPUT_AMPLITUDE = 1 # Peak amplitude in Volts (0.5 V peak = 1 Vpp peak-to-peak)

# Results directory
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


LOG_FILE = Path(__file__).parent / "measurements_log.json"


def load_log() -> dict:
    """Load existing log file or return empty dict if it doesn't exist or is empty."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:

        with open(LOG_FILE, "r") as f:
            return json.load(f)

    return {}


def save_log(log_data: dict) -> None:
    """Save log data to JSON file."""
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run measurements until the specified end datetime.")
    parser.add_argument(
        "--f_sample",
        type = float,
        required=True,
        help='Sample rate in Hz.',
    )
    parser.add_argument(
        "--measurement_duration",
        type = float,
        required=True,
        help='Measurement duration in seconds.',
    )
    parser.add_argument(
        "--description",
        required=False,
        help='Description of the measurement.',
    )
    return parser.parse_args()

def get_date_directory() -> Path:
    """Create and return the hierarchical date-based directory: results/YYYY/MM/DD"""
    now = dt.datetime.now()
    date_dir = RESULTS_DIR / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir

def main() -> None:
    args = parse_args()
    f_sample = args.f_sample
    measurement_duration = args.measurement_duration
    buffer_size = int(measurement_duration * f_sample) + 1
    data_prefix = "first_script"
    description = args.description if args.description else "No description provided"
    MEASUREMENT_TYPE = "single_measurement_laser"
    
    
    start_time = dt.datetime.now()
    start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Load existing log and append new entry
    log_data = load_log()
    log_entry = {
        "start_time": start_time_str,
        "measurement_type": MEASUREMENT_TYPE,
        "description": description,
        "Success": False,
    }
    log_data[start_time_str] = log_entry
    save_log(log_data)
    

    with dwf.Device() as device:
        # Configure clock to be trigger 1 output
        # Set clock mode to output (1 = output, 0 = internal, 2 = input, 3 = IO)
        # device.set_parameter(GlobalParameter.CLOCK_MODE, 1)
        # Set trigger pin 1 to output the clock
        # device.set_trigger(1, TriggerSource.CLOCK)
        # print("Clock configured to output on trigger 1")
        
        # Configure analog output channel 1: sine wave at 1 kHz with 1 Vpp
        # print(f"Configuring analog output channel 1: {OUTPUT_FREQUENCY/1e3:.1f} kHz sine wave, {OUTPUT_AMPLITUDE * 2} Vpp (peak amplitude: {OUTPUT_AMPLITUDE} V)")
        # device.analog_output['ch1'].setup('sine', frequency=OUTPUT_FREQUENCY, amplitude=OUTPUT_AMPLITUDE, offset=0.0, symmetry=50, start=True, configure=True)
        # t.sleep(1)
        
        # Initialize scope
        scope = device.analog_input
        scope[0].setup(range=CHANNEL_RANGE, offset=20.0)
        scope[0].impedance = INPUT_IMPEDANCE 
        scope[0].coupling = AnalogInputCoupling.DC   # Set input impedance (1MΩ or 50Ω)
        scope[1].setup(range=CHANNEL_RANGE, offset=20.0)
        scope[1].impedance = INPUT_IMPEDANCE 
        scope[1].coupling = AnalogInputCoupling.DC # Set input impedance (1MΩ or 50Ω)
        print("acquisition_mode_info",scope.acquisition_mode_info)
        print("acquisition_mode",scope.acquisition_mode)
        scope.acquisition_mode = dwf.AcquisitionMode.SINGLE1
        print("attenuation",scope[0].attenuation)
        print("attenuation",scope[1].attenuation)
        print("scope",dir(scope[1]))
        
        # Get timestamp when measurement starts
        measurement_timestamp = t.strftime("%Y%m%d-%H%M%S")
        
        print(f"Starting measurement at {t.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Sample rate: {f_sample} Hz, Duration: {measurement_duration} s, Buffer size: {buffer_size}")
        
        # Perform single measurement
        scope.single(sample_rate=f_sample, buffer_size=buffer_size, configure=True, start=True)
        
        # Get measurement data
        scope.wait_for_status(dwf.Status.DONE, read_data=True)
        for attr in dir(scope[1]):
            print(attr, getattr(scope[0], attr), (getattr(scope[1], attr)))
        v_pd_1 = scope[0].get_data()  # Voltage in V
        v_pd_2 = scope[1].get_data()
        
        # Get trigger time information from device
        # Returns tuple: (sec_utc, tick, ticks_per_second)
        #   - sec_utc: System time in seconds (UTC, Unix epoch) when trigger occurred
        #   - tick: Sample tick/index in buffer where trigger occurred
        #   - ticks_per_second: Sample rate in ticks/second (should match f_sample)
        trigger_time_info = scope.time
        sec_utc, trigger_tick, ticks_per_second = trigger_time_info
        
        # Create time array for each measurement point (relative to trigger, in seconds)
        # This is the standard approach: time = sample_index / sample_rate
        # Samples are acquired at regular intervals, so time is calculated from sample rate
        time_array = np.arange(len(v_pd_1)) / f_sample
        
        # Optional: Calculate absolute timestamps (UTC seconds) for each sample
        # This combines the trigger system time with relative sample times
        # absolute_timestamps = sec_utc + (trigger_tick + np.arange(len(v_meas))) / ticks_per_second
        
        print(f"Measurement completed. Captured {len(v_pd_1)} samples.")
        print(f"Trigger time info:")
        print(f"  - System time (UTC): {sec_utc} seconds since Unix epoch")
        print(f"  - Trigger tick: {trigger_tick} (sample index where trigger occurred)")
        print(f"  - Ticks per second: {ticks_per_second} (device sample rate)")
        
        # Save v_meas data with timestamp in hierarchical date-based directory
        date_dir = get_date_directory()
        filename = date_dir / f"{data_prefix}_{measurement_timestamp}.json"
        
        # Prepare data dictionary with metadata and measurements
        data_to_save = {
            "timestamp": measurement_timestamp,
            "measurement_time": t.strftime("%Y-%m-%d %H:%M:%S"),
            "sec_utc": int(sec_utc),  # System time in seconds (UTC, Unix epoch)
            "sample_rate_hz": float(f_sample),
            "measurement_duration_s": float(measurement_duration),
            "buffer_size": int(buffer_size),
            "channel_range_v": float(CHANNEL_RANGE),
            "time_s": time_array.tolist(),  # Time array in seconds (relative to trigger)
            "voltage_pd_1": v_pd_1.tolist(),  # Convert numpy array to list for JSON
            "voltage_pd_2": v_pd_2.tolist(),
            # "modulation_frequency_hz": float(OUTPUT_FREQUENCY)
        }
        
        # Save to JSON file
        with open(filename, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        
        print(f"Data saved to: {filename}")
        
    end_time = dt.datetime.now()
    end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Load existing log and append new entry
    log_data = load_log()
    log_entry = {
        "start_time": start_time_str,
        "end_time": end_time_str,
        "measurement_type": MEASUREMENT_TYPE,
        "description": description,
        "Success": True,
    }
    log_data[start_time_str] = log_entry
    save_log(log_data)

if __name__ == "__main__":
    main()