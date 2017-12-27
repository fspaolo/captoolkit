#!/usr/bin/env python
"""
Computes satellite altimeter crossovers.

Calculates location and values at orbit-intersection points by the means of
linear or cubic interpolation between the two/four closest records to the
crossover location for ascending and descending orbits.

Notes: 
    The program needs to have an input format according as followed:
    orbit nr., latitude (deg), longitude (deg), time (yr), surface height (m).

    The crossover location is rejected if any of the four/eight closest
    records has a distance larger than an specified threshold, provided by
    the user. To reduce the crossover computational time the input data can
    be divided into tiles, where each tile is solved independently of the
    others. This reduced the number of obs. in the inversion to calculate the
    crossing position. The input data can further be reprojected, give user
    input, to any wanted projection. Changing the projection can help to
    improve the estimation of the crossover location, due to improved
    geometry of the tracks (straighter). For each crossover location the
    closest records are linearly interpolated using 1D interpolation, by
    using the first location in each track (ascending and descending) as a
    distance reference. The user can also provide a resolution parameter used
    to determine how many point (every n:th point) to be used for solving for
    the crossover intersection to improve computation speed. However, the
    closest points are still used for interpolation of the records to the
    crossover location. The program can also be used for inter-mission
    elevation change rate and bias estimation, which requires the mission to
    provide a extra column with satellite mission indexes.

Args:
    ifile: Name of input file, if ".npy" data is read as binary.
    ofile: Name of output file, if ".npy" data is saved as binary
    icols: String of indexes of input columns: "orb lat lon t h".
    radius: Cut-off radius (from crossing pt) for accepting crossover (m).
    proj: EPSG projection number (int).
    dxy: Tile size (km).
    nres: Track resolution: Use n:th for track intersection (int).
    buff: Add buffer around tile (km)
    mode: Interpolation mode "linear" or "cubic".
    mission: Inter-mission rate or bias estimation "True", "False"

Example:
    xover2.py ~/data/xover/vostok/unc/RA2_D_ICE_A.h5 \
            -v orbit orb_type lon lat t_year h_res -t 2003 2009 -d 50 -p 3031

"""
import os
import sys
import numpy as np
import pyproj
import h5py
import argparse
import warnings
import pandas as pd
from scipy.interpolate import InterpolatedUnivariateSpline

# Ignore all warnings
warnings.filterwarnings("ignore")


def get_args():
    """ Get command-line arguments. """
    parser = argparse.ArgumentParser(
            description='Program for computing satellite/airborne crossovers.')
    parser.add_argument(
            'input', metavar='ifile', type=str, nargs=2,
            help='name of two input files to cross (HDF5 or ASCII)')
    parser.add_argument(
            '-o', metavar='ofile', dest='output', type=str, nargs=1,
            help='name of output file (HDF5 or ASCII, acording input type)',
            default=[None])
    parser.add_argument(
            '-r', metavar=('radius'), dest='radius', type=float, nargs=1,
            help='maximum interpolation distance from crossing location (m)',
            default=[350],)
    parser.add_argument(
            '-p', metavar=('epsg_num'), dest='proj', type=str, nargs=1,
            help=('projection: EPSG number (AnIS=3031, GrIS=3413)'),
            default=['4326'],)
    parser.add_argument(
            '-d', metavar=('tile_size'), dest='dxy', type=int, nargs=1,
            help='tile size (km)',
            default=[0],)
    parser.add_argument(
            '-k', metavar=('subsample'), dest='nres', type=int, nargs=1,
            help='along-track subsampling every k:th point (for speed up)',
            default=[1],)
    parser.add_argument(
            '-b', metavar=('buffer'), dest='buff', type=int, nargs=1,
            help=('tile buffer (km)'),
            default=[0],)
    parser.add_argument(
            '-m', metavar=None, dest='mode', type=str, nargs=1,
            help='interpolation method, "linear" or "cubic"',
            choices=('linear', 'cubic'), default=['linear'],)
    parser.add_argument(
            '-c', metavar=('0','1','2','3','4'), dest='cols', type=int, nargs=5,
            help='main vars: col# if ASCII, orbit/lon/lat/time/height',
            default=[0,2,1,3,4],)
    parser.add_argument(
            '-v', metavar=('o','x','y','t','h'), dest='vnames', type=str, nargs=5,
            help=('main vars: names if HDF5, orbit/lon/lat/time/height'),
            default=[None],)
    parser.add_argument(
            '-t', metavar=('t1','t2'), dest='tspan', type=float, nargs=2,
            help='only compute crossovers for given time span',
            default=[None],)
    return parser.parse_args()


def intersect(x_down, y_down, x_up, y_up):
    """ Find orbit crossover locations. """
    
    p = np.column_stack((x_down, y_down))
    q = np.column_stack((x_up, y_up))

    (p0, p1, q0, q1) = p[:-1], p[1:], q[:-1], q[1:]
    rhs = q0 - p0[:, np.newaxis, :]

    mat = np.empty((len(p0), len(q0), 2, 2))
    mat[..., 0] = (p1 - p0)[:, np.newaxis]
    mat[..., 1] = q0 - q1
    mat_inv = -mat.copy()
    mat_inv[..., 0, 0] = mat[..., 1, 1]
    mat_inv[..., 1, 1] = mat[..., 0, 0]

    det = mat[..., 0, 0] * mat[..., 1, 1] - mat[..., 0, 1] * mat[..., 1, 0]
    mat_inv /= det[..., np.newaxis, np.newaxis]

    import numpy.core.umath_tests as ut

    params = ut.matrix_multiply(mat_inv, rhs[..., np.newaxis])
    intersection = np.all((params >= 0) & (params <= 1), axis=(-1, -2))
    p0_s = params[intersection, 0, :] * mat[intersection, :, 0]

    return p0_s + p0[np.where(intersection)[0]]


def transform_coord(proj1, proj2, x, y):
    """ Transform coordinates from proj1 to proj2 (EPSG num). """

    # Set full EPSG projection strings
    proj1 = pyproj.Proj("+init=EPSG:"+str(proj1))
    proj2 = pyproj.Proj("+init=EPSG:"+str(proj2))

    # Convert coordinates
    return pyproj.transform(proj1, proj2, x, y)


def get_bboxs(xmin, xmax, ymin, ymax, dxy):
    """
    Define blocks (bbox) for speeding up the processing. 

    Args:
        xmin/xmax/ymin/ymax: must be in grid projection: stereographic (m).
        dxy: grid-cell size.
    """
    # Number of tile edges on each dimension 
    Nns = int(np.abs(ymax - ymin) / dxy) + 1
    New = int(np.abs(xmax - xmin) / dxy) + 1

    # Coord of tile edges for each dimension
    xg = np.linspace(xmin, xmax, New)
    yg = np.linspace(ymin, ymax, Nns)

    # Vector of bbox for each cell
    bboxs = [(w,e,s,n) for w,e in zip(xg[:-1], xg[1:]) 
                       for s,n in zip(yg[:-1], yg[1:])]
    del xg, yg

    return bboxs


# Read in parameters
args = get_args()
ifiles  = args.input[:]
ofile_ = args.output[0]
radius = args.radius[0]
proj   = args.proj[0]
dxy    = args.dxy[0]
nres   = args.nres[0]
buff   = args.buff[0]
mode   = args.mode[0]
icols  = args.cols[:]
vnames = args.vnames[:]
tspan = args.tspan[:]

print 'parameters:'
for arg in vars(args).iteritems(): print arg

# Get column numbers
(co, cx, cy, ct, cz) = icols

# Get variable names
ovar, xvar, yvar, tvar, zvar = vnames 

# Test for stereographic
if proj != "4326":

    # Convert to meters
    dxy *= 1e3


def filter(x, y):
    x[(np.isnan(y)) | (y==0.)] = np.nan
    return x


def main(ifile1, ifile2):
    """ Find and compute crossover values. """

    print 'crossing files:', ifile1, ifile2, '...'

    # Load all 1d variables needed
    with h5py.File(ifile1, 'r') as f1, \
         h5py.File(ifile2, 'r') as f2:

        ##### TODO: Edit
        #zvar = 'h_res'          # dh w.r.t. topo + slp cor + bs cor
        #zvar = 'h_cor'          # h + slp cor 
        #zvar = 'h_cor_orig'     # h
        #####

        if zvar == 'h_res' or zvar == 'h_cor':
            xvar = 'lon'
            yvar = 'lat'
        else:
            xvar = 'lon_orig'
            yvar = 'lat_orig'

        if zvar == 'h_res':
            zvar_ice = 'h_res'
        else:
            zvar_ice = 'h_cor'
             
        # ICESat
        orbit1 = f1['orbit'][:]
        time1 = f1['t_year'][:]
        lon1 = f1['lon'][:]       # always the same for ICESat
        lat1 = f1['lat'][:]
        height1 = f1[zvar_ice][:]

        # RA
        orbit2 = f2['orbit'][:]
        time2 = f2['t_year'][:]
        lon2 = f2[xvar][:]
        lat2 = f2[yvar][:]
        height2 = f2[zvar][:]

        try:
            h_bs = f2['h_bs'][:]
            h_bs[h_bs==0] = np.nan

            if zvar == 'h_res':
                height2[np.isnan(h_bs)] = np.nan  # only filter
            else:
                height2 -= h_bs                   # bs correct

        except:
            print 'uncorrected heights!'          # do nothing
            

    # If time span given, filter out invalid data
    if len(tspan) > 1:

        t1, t2 = tspan

        idx, = np.where((time1 >= t1) & (time1 <= t2))
        orbit1 = orbit1[idx]
        lon1 = lon1[idx]
        lat1 = lat1[idx]
        time1 = time1[idx]
        height1 = height1[idx]

        idx, = np.where((time2 >= t1) & (time2 <= t2))
        orbit2 = orbit2[idx]
        lon2 = lon2[idx]
        lat2 = lat2[idx]
        time2 = time2[idx]
        height2 = height2[idx]

        if len(time1) < 3 or len(time2) < 3:
            print 'there are no points within time-span specified!'
            sys.exit()

    # Transform to wanted coordinate system
    (xp1, yp1) = transform_coord(4326, proj, lon1, lat1)
    (xp2, yp2) = transform_coord(4326, proj, lon2, lat2)

    # Time limits: the largest time span (yr)
    tmin = min(np.nanmin(time1), np.nanmin(time2))
    tmax = max(np.nanmax(time1), np.nanmax(time2))

    # Boundary limits: the smallest spatial domain (m)
    xmin = max(np.nanmin(xp1), np.nanmin(xp2))
    xmax = min(np.nanmax(xp1), np.nanmax(xp2))
    ymin = max(np.nanmin(yp1), np.nanmin(yp2))
    ymax = min(np.nanmax(yp1), np.nanmax(yp2))

    # Interpolation type and number of needed points
    if mode == "linear":
        # Linear interpolation
        nobs  = 2
        order = 1

    else:
        # Cubic interpolation
        nobs  = 4
        order = 3

    # Tiling option - "on" or "off"
    if dxy != 0:
        bboxs = get_bboxs(xmin, xmax, ymin, ymax, dxy)

    else:
        bboxs = [(xmin, xmax, ymin, ymax)]  # full domain

    print 'number of sub-tiles:', len(bboxs)

    # Initiate output container (much larger than it needs to be)
    out = np.full((len(orbit1)+len(orbit2), 8), np.nan)

    # Plot for testing
    if 1:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(lon1, lat1, '.')
        plt.figure()
        plt.plot(lon2, lat2, '.')
        plt.show()
        sys.exit()

    # Initiate xover counter
    i_xover = 0

    # Loop through each sub-tile
    for k,bbox in enumerate(bboxs):

        print 'tile #', k

        # Bounding box of grid cell
        xmin, xmax, ymin, ymax = bbox

        # Get the tile indices
        idx1, = np.where( (xp1 >= xmin - buff) & (xp1 <= xmax + buff) & 
                          (yp1 >= ymin - buff) & (yp1 <= ymax + buff) )

        idx2, = np.where( (xp2 >= xmin - buff) & (xp2 <= xmax + buff) & 
                          (yp2 >= ymin - buff) & (yp2 <= ymax + buff) )

        # Extract tile data from each set 
        orbits1 = orbit1[idx1]
        lons1 = lon1[idx1]
        lats1 = lat1[idx1]
        x1 = xp1[idx1]
        y1 = yp1[idx1]
        h1 = height1[idx1]
        t1 = time1[idx1]

        orbits2 = orbit2[idx2]
        lons2 = lon2[idx2]
        lats2 = lat2[idx2]
        x2 = xp2[idx2]
        y2 = yp2[idx2]
        h2 = height2[idx2]
        t2 = time2[idx2]

        orb_ids1 = np.unique(orbits1)
        orb_ids2 = np.unique(orbits2)

        # Test if tile has no xovers
        if len(orbits1) == 0 or len(orbits2) == 0:
            continue

        # Loop through orbits from file #1
        for orb_id1 in orb_ids1:

            # Index for single ascending orbit
            i_trk1 = orbits1 == orb_id1 

            # Extract points from single orbit (a track)
            xa = x1[i_trk1]
            ya = y1[i_trk1]
            ta = t1[i_trk1]
            ha = h1[i_trk1]

            # Loop through tracks from file #2
            for orb_id2 in orb_ids2:

                # Index for single descending orbit
                i_trk2 = orbits2 == orb_id2

                # Extract single orbit
                xb = x2[i_trk2]
                yb = y2[i_trk2]
                tb = t2[i_trk2]
                hb = h2[i_trk2]

                # Test length of vector
                if len(xa) < 3 or len(xb) < 3:
                    continue
                
                # Initial crossing test -  start and end points
                cxy_intial = intersect(xa[[0, -1]], ya[[0, -1]], xb[[0, -1]], yb[[0, -1]])
                
                # Test for crossing
                if len(cxy_intial) == 0:
                    continue

                # Compute exact crossing - full set of observations, or every n:th point
                cxy_main = intersect(xa[::nres], ya[::nres], xb[::nres], yb[::nres])

                # Test again for crossing
                if len(cxy_main) == 0:
                    continue

                # Extract crossing coordinates
                xi = cxy_main[0][0]
                yi = cxy_main[0][1]

                # Get start coordinates of orbits
                xa0 = xa[0]
                ya0 = ya[0]
                xb0 = xb[0]
                yb0 = yb[0]

                # Compute distance from crossing node to each arc
                da = (xa - xi) * (xa - xi) + (ya - yi) * (ya - yi)
                db = (xb - xi) * (xb - xi) + (yb - yi) * (yb - yi)

                # Sort according to distance
                Ida = np.argsort(da)
                Idb = np.argsort(db)

                # Sort arrays - A
                xa = xa[Ida]
                ya = ya[Ida]
                ta = ta[Ida]
                ha = ha[Ida]
                da = da[Ida]

                # Sort arrays - B
                xb = xb[Idb]
                yb = yb[Idb]
                tb = tb[Idb]
                hb = hb[Idb]
                db = db[Idb]

                # Get distance of four closest observations
                dab = np.vstack((da[[0, 1]], db[[0, 1]]))

                # Test if any point is too far away
                if np.any(np.sqrt(dab) > radius):
                    continue

                # Test if enough obs. are available for interpolation
                if (len(xa) < nobs) or (len(xb) < nobs):
                    continue

                # Compute distance again from the furthest point
                da0 = (xa - xa0) * (xa - xa0) + (ya - ya0) * (ya - ya0)
                db0 = (xb - xb0) * (xb - xb0) + (yb - yb0) * (yb - yb0)

                # Compute distance again from the furthest point
                dai = (xi - xa0) * (xi - xa0) + (yi - ya0) * (yi - ya0)
                dbi = (xi - xb0) * (xi - xb0) + (yi - yb0) * (yi - yb0)

                ##TODO: Try interpolation with np.interp1d()!

                # Interpolate height to crossover location
                Fhai = InterpolatedUnivariateSpline(da0[0:nobs], ha[0:nobs], k=order)
                Fhbi = InterpolatedUnivariateSpline(db0[0:nobs], hb[0:nobs], k=order)

                # Interpolate time to crossover location
                Ftai = InterpolatedUnivariateSpline(da0[0:nobs], ta[0:nobs], k=order)
                Ftbi = InterpolatedUnivariateSpline(db0[0:nobs], tb[0:nobs], k=order)
                
                # Get interpolated values - height
                hai = Fhai(dai)
                hbi = Fhbi(dbi)

                # Get interpolated values - time
                tai = Ftai(dai)
                tbi = Ftbi(dbi)
                
                # Test interpolate time values
                if (tai > tmax) or (tai < tmin) or (tbi > tmax) or (tbi < tmin):
                    continue
                
                # Compute differences and save parameters
                out[i_xover,0] = xi
                out[i_xover,1] = yi
                out[i_xover,2] = hai - hbi
                out[i_xover,3] = tai - tbi
                out[i_xover,4] = tai
                out[i_xover,5] = tbi
                out[i_xover,6] = hai
                out[i_xover,7] = hbi

                # Increment counter
                i_xover += 1

    # Remove invalid rows 
    out = out[~np.isnan(out[:,2]),:]

    # Test if output container is empty 
    if len(out) == 0:
        print 'no crossovers found!'
        return

    # Remove the two id columns if they are empty 
    out = out[:,:-2] if np.isnan(out[:,-1]).all() else out

    # Transform coords back to lat/lon
    out[:,0], out[:,1] = transform_coord(proj, '4326', out[:,0], out[:,1])

    # Name of each variable
    fields = ['lon', 'lat', 'dh', 'dt', 't1', 't2', 'h1', 'h2']

    # Create output file name if not given 
    if ofile_ is None:
        path, ext = os.path.splitext(ifile)
        ofile = path + '_xover' + ext
    else:
        ofile = ofile_
        
    # Determine data format
    if ofile.endswith('.npy'):
        
        # Save as binary file
        np.save(ofile, out)

    elif ofile.endswith(('.h5', '.H5', '.hdf', '.hdf5')):

        # Create h5 file
        with h5py.File(ofile, 'w') as f:
            
            # Loop through fields
            [f.create_dataset(k, data=d) for k,d in zip(fields, out.T)]

    else:

        # Save data to ascii file
        np.savetxt(ofile, out, delimiter="\t", fmt="%8.5f")

    print 'ouput ->', ofile


if __name__ == '__main__':

    file1, file2 = ifiles
    main(file1, file2)
