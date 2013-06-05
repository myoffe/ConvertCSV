ConvertCSV
==========

Script to convert provider rates CSV to standard CSV format, for later insertion into a database table.

## Usage
In terminal, go to script directory and run

    python convert.py vodafone|tmobile|sprint <infile> <outfile>

## Examples
    python convert.py tmobile input/tmobile.csv output/tmobile.csv
    python convert.py vodafone input/vodafone.csv output/vodafone.csv
    python convert.py sprint input/sprint.csv output/sprint.csv
  
See CSVs in input folder for input examples, and CSVs in output/examples for how the output should look.
  
## TODO
1. Auto detect format and use converter accordingly

  
