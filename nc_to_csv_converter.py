import sys
import os
import argparse
import xarray as xr
import pandas as pd
import netCDF4 as nc
import numpy as np

def find_variables_in_groups(dataset, group_path=""):
    """Recursively search for variables inside NetCDF4 groups."""
    found_vars = {}
    
    if dataset.variables:
        found_vars[group_path] = list(dataset.variables.keys())
        
    for group_name, group_obj in dataset.groups.items():
        sub_path = f"{group_path}/{group_name}" if group_path else group_name
        found_vars.update(find_variables_in_groups(group_obj, sub_path))
        
    return found_vars

def extract_via_netcdf4(input_path: str, output_path: str, target_var: str = None):
    """
    Fallback method using netCDF4 library, with group-level traversal 
    and date-decoding for numeric time units.
    """
    print("--------------------------------------------------")
    print("Xarray detected 0 root variables. Scanning NetCDF structure...")
    
    if os.path.getsize(input_path) == 0:
        print(f"Error: File '{input_path}' is completely empty (0 bytes).")
        sys.exit(1)

    dataset = nc.Dataset(input_path)
    all_groups_vars = find_variables_in_groups(dataset)
    
    target_group = None
    var_keys = []
    
    for g_path, v_keys in all_groups_vars.items():
        if len(v_keys) > 0:
            target_group = g_path
            var_keys = v_keys
            break
            
    if not var_keys:
        print("Error: No variables found anywhere in this file.")
        sys.exit(1)

    print(f"Found variables in group '{target_group if target_group else 'root'}': {var_keys}")
    active_ds = dataset if not target_group else dataset[target_group]
    
    # Identify coordinate keys
    lat_key = next((k for k in ['latitude', 'lat', 'lats'] if k in var_keys), None)
    lon_key = next((k for k in ['longitude', 'lon', 'lons'] if k in var_keys), None)
    time_key = next((k for k in ['time', 'date', 'times'] if k in var_keys), None)
    
    # Identify target data variable
    if not target_var:
        candidates = ['rain', 'tp', 'precip', 'pr', 'precipitation', 'RAINFALL', 'rf', 'rainfall', 'RainFall', '']
        for cand in candidates:
            if cand in var_keys:
                target_var = cand
                break
                
    if not target_var:
        ignore = {lat_key, lon_key, time_key, 'spatial_ref', 'crs', '_NCProperties'}
        remaining = [k for k in var_keys if k not in ignore]
        if remaining:
            target_var = remaining[0]
            
    if not target_var or target_var not in var_keys:
        print(f"Error: Could not locate rainfall data variable. Available: {var_keys}")
        sys.exit(1)
        
    print(f"Processing target variable: '{target_var}'")
    
    # Extract arrays
    lats = active_ds.variables[lat_key][:]
    lons = active_ds.variables[lon_key][:]
    raw_times = active_ds.variables[time_key]
    data = active_ds.variables[target_var][:]
    
    # --- DECODE NUMERIC TIME TO CALENDAR DATES ---
    time_var = active_ds.variables[time_key]
    time_vals = time_var[:]
    
    if hasattr(time_var, 'units'):
        units = time_var.units
        calendar = getattr(time_var, 'calendar', 'standard')
        try:
            # Convert numbers (0, 1, 2) to actual datetime objects
            decoded_times = nc.num2date(time_vals, units=units, calendar=calendar)
            # Format as YYYY-MM-DD
            formatted_times = [pd.to_datetime(str(t)).strftime('%Y-%m-%d') for t in decoded_times]
        except Exception as e:
            print(f"Warning: Could not decode time units '{units}'. Error: {e}")
            formatted_times = time_vals
    else:
        formatted_times = time_vals

    # Mesh grid coordinates and convert to DataFrame
    mesh_time, mesh_lat, mesh_lon = np.meshgrid(formatted_times, lats, lons, indexing='ij')
    
    df = pd.DataFrame({
        'date': mesh_time.flatten(),
        'latitude': mesh_lat.flatten(),
        'longitude': mesh_lon.flatten(),
        target_var: data.flatten()
    }).dropna(subset=[target_var])
    print(f"Processed target variable: '{target_var}' and coverted into Dataframe.")
    print("--------------------------------------------------\n")
    
    # Pivot into grid matrix
    print("--------------------------------------------------")
    print(f"Started to converting the date as rows and lat, long as columns...")
    df['grid_cell'] = 'lat_' + df['latitude'].astype(str) + '_lon_' + df['longitude'].astype(str)
    final_df = df.pivot(index='date', columns='grid_cell', values=target_var).reset_index()
    print(f"Converted and Started to saving this...")
    print("--------------------------------------------------\n")
    final_df.to_csv(output_path, index=False)
    
    print("--------------------------------------------------")
    print(f"Success! Output saved to: {output_path}")
    print(f"Total time steps (rows): {len(final_df)}")
    print(f"Total spatial points (columns): {len(final_df.columns) - 1}")
    print("--------------------------------------------------\n")

def convert_nc_to_csv(input_path: str, output_path: str, target_var: str = None):
    print(f"Opening file: {input_path}...\n")
    
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' does not exist.")
        sys.exit(1)

    try:
        ds = xr.open_dataset(input_path, engine="netcdf4", decode_coords="all")
    except Exception:
        try:
            ds = xr.open_dataset(input_path, engine="netcdf4", decode_times=True)
        except Exception:
            extract_via_netcdf4(input_path, output_path, target_var)
            return

    if len(ds.data_vars) == 0:
        extract_via_netcdf4(input_path, output_path, target_var)
        return

    # Standard Xarray path
    if not target_var:
        common_names = ['rain', 'tp', 'precip', 'pr', 'precipitation']
        for var in common_names:
            if var in ds.data_vars:
                target_var = var
                break
        if not target_var:
            target_var = list(ds.data_vars.keys())[0]

    print(f"Processing variable: '{target_var}'...")

    df = ds.to_dataframe().reset_index().dropna(subset=[target_var])

    lat_col = next((c for c in ['latitude', 'lat'] if c in df.columns), None)
    lon_col = next((c for c in ['longitude', 'lon'] if c in df.columns), None)
    time_col = next((c for c in ['time', 'date'] if c in df.columns), None)

    # Format datetime if xarray produced datetime objects
    if pd.api.types.is_datetime64_any_dtype(df[time_col]):
        df[time_col] = df[time_col].dt.strftime('%Y-%m-%d')

    df['grid_cell'] = 'lat_' + df[lat_col].astype(str) + '_lon_' + df[lon_col].astype(str)
    final_df = df.pivot(index=time_col, columns='grid_cell', values=target_var).reset_index()

    final_df.to_csv(output_path, index=False)
    
    print("--------------------------------------------------")
    print(f"Success! Output saved to: {output_path}")
    print(f"Total time steps (rows): {len(final_df)}")
    print(f"Total spatial points (columns): {len(final_df.columns) - 1}")
    print("--------------------------------------------------")

def main():
    parser = argparse.ArgumentParser(
        description="Convert spatial NetCDF rainfall files (.nc) to time-series CSV matrices."
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input .nc file")
    parser.add_argument("-o", "--output", default="rainfall_output.csv", help="Path for output .csv file")
    parser.add_argument("-v", "--variable", required=False, help="Target NetCDF variable name")

    args = parser.parse_args()
    convert_nc_to_csv(args.input, args.output, args.variable)

if __name__ == "__main__":
    main()