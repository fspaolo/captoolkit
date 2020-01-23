![splash](splash.png)

# captoolkit - JPL Cryosphere Altimetry Processing Toolkit

Set of tools for processing and integrating satellite and airborne altimetry data.

## Credits

* [Fernando Paolo](https://science.jpl.nasa.gov/people/Serrano%20Paolo/) (paolofer@jpl.nasa.gov) - Main developer
* [Johan Nilsson](https://science.jpl.nasa.gov/people/Nilsson/) (johan.nilsson@jpl.nasa.gov) - Main developer
* [Alex Gardner](https://science.jpl.nasa.gov/people/AGardner/) (alex.s.gardner@jpl.nasa.gov) - Project PI

Jet Propulsion Laboratory, California Institute of Technology

## Install

    git clone https://github.com/fspaolo/captoolkit.git
    cd captoolkit
    python setup.py install

## Example

Read ICESat-2 (ATL06) data files and extract some variables using 4 cores (from the command line):

    readatl06.py -n 4 *.h5 

To see the imput arguments of each program run:

    program.py -h

For more information check the header of each program.

## Notebooks

* [Introduction to HDF5 data files](https://nbviewer.jupyter.org/github/fspaolo/captoolkit/blob/master/notebooks/intro-to-hdf5.ipynb)  
  High-level overview of the HDF5 file structure and associated tools

* [Reduction of ICESat-2 data files](https://nbviewer.jupyter.org/github/fspaolo/captoolkit/blob/master/notebooks/redu-is2-files.ipynb)  
  Select (ATL06) files and variables of interest and write to a simpler structure
  
* [Filtering and gridding elevation change observations](https://nbviewer.jupyter.org/github/fspaolo/captoolkit/blob/master/notebooks/Gridding-rendered.ipynb)  
  Interpolation and filtering approaches to derive gridded products of elevation change

## Notes

This package is under development, and new tools are being added as we finish testing them (more utilities are coming).

Currently, the individual programs work as standalone command-line utilities. There is no need to install the package. You can simply run the python scripts as:

    python program.py -a arg1 -b arg2 /path/to/files/*.h5

## Tools

### Reading

* `readgeo.py` - Read Geosat and apply/remove corrections
* `readers.py` - Read ERS (REAPER) and apply/remove corrections
* `readra2.py` - Read Envisat and apply/remove corrections
* `readgla12.py` - Read ICESat GLA12 Release 634 HDF5 and apply/remove corrections
* `readatl06.py` - Read ICESat-2 ATL06 HDF5 and select specific variables

### Correcting

* `corrapply.py` 
* `corrslope.py` - Correct slope-induced errors using 'direct' or 'relocation' method 
* `corrscatt.py` - Correct radar altimetry height to correlation with waveform parameters
* `corrlaser.py`

### Filtering

* `filtmask.py` - Select scattered data using raster-mask, polygon or bounding box
* `filtnan.py`

### Differencing

* `xing.py`
* `xover.py` - Compute crossover values at satellite orbit intersections

### Fitting

* `fittopo.py` - Detrend data with respect to modeled topography
* `fitsec.py` - Compute robust height changes using a surface-fit approach

### Interpolating

* `interpgaus.py` - Interpolate irregular data using Gaussian Kernel
* `interpkrig.py` - Interpolate irregular data using Kriging/Collocation

### Utilities

* `gettopo.py` - Estimate slope, aspect and curvature from given DEM
* `split.py` - Split large 1D HDF5 file(s) into smaller ones
* `merge.py` - Merge several HDF5 files into a single or multiple file(s)
* `mergetile.py` - Merge tiles from different missions keeping the original grid
* `tile.py` - Tile geographical (point) data to allow parallelization
* `join.py` - Join a set of geographical tiles (individual files)
* `joingrd.py` 
* `sort.py` - Sort (in place) all 1D variables in HDF5 file(s)
* `dummy.py` - Add dummy variables as 1D arrays to HDF5 files(s)
* `hdf2txt.py` - Convert HDF5 (1D arrays) to ASCII tables (columns)
* `txt2hdf.py` - Convert (very large) ASCII tables to HDF5 (1D arrays)
