# captoolbox - JPL Cryosphere Altimetry Processing Toolbox

Set of tools for processing and integrating satellite and airborne altimetry data.

## Credits

* [Johan Nilsson](https://science.jpl.nasa.gov/people/Nilsson/) (johan.nilsson@jpl.nasa.gov) - Core developer
* [Fernando Paolo](https://science.jpl.nasa.gov/people/Serrano%20Paolo/) (paolofer@jpl.nasa.gov) - Core developer
* [Alex Gardner](https://science.jpl.nasa.gov/people/AGardner/) (alex.s.gardner@jpl.nasa.gov) - Project PI

Jet Propulsion Laboratory, California Institute of Technology

## Installation

    git clone https://github.com/fspaolo/captoolbox.git
    cd captoolbox
    python setup.py install

## Utilities

* `readglas.py` - Reads GLA12 Release 634 HDF5 and applies/remove corrections
* `readra.py` -  Reads ERS (REAPER) and applies/remove corrections
* `readra2.py` -  Reads Envisat and applies/remove corrections

* `slp2ibe.py` - Converts ERA-Interim Sea-level pressure to Inverse Barometer Effect (IBE)
* `ibecor.py` - Computes and applies the inverse barometer correction (IBE) to height data
* `tidecor.py` - Computes and applies tide corrections (using a 3rd-party software)
* `slopecor.py` - Corrects for slope-induced errors, using the 'direct' or 'relocation' method
* `scattcor.py` - Corrects radar altimetry height to correlation with waveform parameters

* `cs2proc.py` - Processes Cryosat-2 SARIn mode data
* `topofit.py` - Detrends data with respect to mean topography (linear or quadratic surface)
* `secfit.py` - Computes robust height changes using a surface-fit approach
* `xover.py` - Computes crossover values at satellite orbit intersections
* `merge.py` - Merges heterogeneous multi-mission data, and performs optimal interpolation

* `setorbit.py` - Calculates unique identifiers for each multi-mission track (segments of data)
* `reftrack.py` - Identifies repeat tracks and calculates the reference ground tracks
* `septrack.py` - Separates orbit arcs into ascending and descending tracks
* `sepcampg.py` - Separates data points into campaigns (specified time intervals)

* `sortvars.py` - Sort (in place) all 1d variables in HDF5 file(s)
* `dummy.py` - Adds dummy variables as 1d arrays to HDF5 files(s)
* `txt2hdf.py` - Converts (very large) ASCII tables to HDF5 (1d arrays)
* `hdf2txt.py` - Converts HDF5 (1d-arrays) to ASCII (columns)

* `split.py` - Splits large 1d HDF5 file(s) into smaller ones
* `tile.py` - Tiles geographical data to reduce data volumes and allow parallelization
* `join.py` - Joins a set of geographical tiles (individual files)
* `merge.py` - Merges several HDF5 files into a single file or multiple larger files
* `mergetiles.py` - Merges tiles from different missions keeping the original tiling (grid)
