# NC_to_CSV_Converter_tool

A scope to converts a multi-dimensional NetCDF file into a time-series CSV where we need the Rows are Dates / Time steps and the columns are individual Lat/Lon pairs.

## Description

A lightweight Python utility designed to convert multi-dimensional spatial NetCDF (`.nc`) weather datasets (such as IMD gridded data) into standard time-series CSV matrices.

## Features
- Automatically detects coordinates (`latitude`, `longitude`, `time`).
- Automatically detects variable names (`rain`, `tp`, `precip`, etc.).
- Converts 3D spatial grids into wide-format matrices where columns represent explicit `lat_lon` points.
- Optimized using vectorized Pandas operations for maximum speed.

## Installation

```
bash
git clone [https://github.com/svmhub/NC_to_CSV_Coverter_tool.git](https://github.com/svmhub/NC_to_CSV_Coverter_tool.git)
cd YOUR_REPO_NAME
pip install -r requirements.txt
```

## Usage

- Run directly from your terminal

    **python converter.py -i input_file_name.nc -o output_file_name.csv**
  
- Optional arguments:   

  -i or --input: Input NetCDF file path (Required)   
  -o or --output: Output CSV file path (Default: rainfall_output.csv)   
  -v or --variable: Target NetCDF variable name (Optional)   

> This would be helpful to the researchers and their laboratories. Kindly take it and enjoy your time.

## Hence I have completed the tool successfully! 🫰😍
