import global_config as G
import numpy as np

from astropy.io import fits as pyfits
from astropy.coordinates import Angle
import os.path as op

log = G.logging.getLogger('hetdex_logger')
log.setLevel(G.logging.DEBUG)


class HetdexFits:
    '''A single HETDEX fits file ... 2D spectra, expected to be science file'''

    #needs open with basic validation
    #

    def __init__(self,fn,e_fn,fe_fn,dither_index=-1,panacea=False):
        self.okay = True
        self.filename = fn
        self.err_filename = e_fn
        self.fe_filename = fe_fn

        self.panacea = panacea

        self.tel_ra = None
        self.tel_dec = None
        self.parangle = None
        self.ifuid = None # reminder this is the cable
        self.ifuslot = None # reminder this is the position (slot) on the fplane
        self.side = None
        self.amp = None
        self.specid = None
        self.obs_date = None
        self.obs_ymd = None
        self.mjd = None
        self.obsid = None
        self.expid = None
        self.imagetype = None
        #self.exptime = None #don't need these right now
        #self.dettemp = None #don't need these right now

        self.data = None
        self.err_data = None
        self.fe_data = None #fiber extracted counts
        self.wave_data = None #matched wavelengths
        self.trace_data = None
        self.pixflat_data = None
        self.fiber_centers = None
        self.fe_crval1 = None
        self.fe_cdelt1 = None

        self.dither_index = dither_index

        #build basic info from filename

        #determine if 'cure'-style fits or panacea fits
        #stupid simple just for now
        if "multi_" in self.filename: # example: multi_020_095_004_LU.fits
            self.read_panacea_fits()
        else:
            self.read_fits(use_cosmic_cleaned=G.PreferCosmicCleaned)
            self.read_efits(use_cosmic_cleaned=G.PreferCosmicCleaned)
            self.read_fefits()

    def read_fits(self,use_cosmic_cleaned=False):

        if not self.filename:
            return None

        if not op.exists(self.filename):
            log.error("Error. FITS file does not exist: " + self.filename)
            return None

        try:
            f = pyfits.open(self.filename)
        except:
            log.error("could not open file " + self.filename, exc_info=True)
            return None

        c = None
        try:
            if use_cosmic_cleaned:
                base = op.basename(self.filename)
                if base[0] != 'c':
                    path = op.dirname(self.filename)

                    cosmic = op.join(path,"c"+base)
                    log.info("Attempting to open cosmic cleaned version of file: " + cosmic)
                    c = pyfits.open(cosmic)
        except:
            log.error("could not open file " + cosmic, exc_info=True)
            c = None


        if c is not None:
            self.data = np.array(c[0].data)
        else:
            self.data = np.array(f[0].data)
        #clean up any NaNs
        self.data[np.isnan(self.data)] = 0.0

        try:
            self.tel_ra = float(Angle(f[0].header['TELRA']+"h").degree) #header is in hour::mm:ss.arcsec
            self.tel_dec = float(Angle(f[0].header['TELDEC']+"d").degree) #header is in deg:hh:mm:ss.arcsec
            self.parangle = f[0].header['PARANGLE']
        except:
            log.error("Cannot translate RA and/or Dec from FITS format to degrees in " + self.filename, exc_info=True)

        try:
            self.ifuid = str(f[0].header['IFUID']).zfill(3)
            self.ifuslot = str(f[0].header['IFUSLOT']).zfill(3)
            self.side = f[0].header['CCDPOS']
            self.specid = str(f[0].header['SPECID']).zfill(3)
            self.obs_date = f[0].header['DATE-OBS']

            if '-' in self.obs_date: #expected format is YYYY-MM-DD
                self.obs_ymd = self.obs_date.replace('-','')
            self.mjd = f[0].header['MJD']
            self.obsid = f[0].header['OBSID']
            self.imagetype = f[0].header['IMAGETYP']
            #self.exptime = f[0].header['EXPTIME']
            #self.dettemp = f[0].header['DETTEMP']
        except:
            log.error("Cannot read expected keywords in fits header: " + self.filename,exc_info=True)
            self.okay = False

        try:
            f.close()
        except:
            log.error("could not close file " + self.filename, exc_info=True)

        if c is not None:
            try:
                c.close()
            except:
                log.error("could not close file cosmic file version of " + self.filename, exc_info=True)
        return

    def read_efits(self,use_cosmic_cleaned=False):

        if self.err_filename is None:
            return None

        try:
            f = pyfits.open(self.err_filename)
        except:
            log.error("could not open file " + self.err_filename, exc_info=True)
            return None

        c = None
        try:
            if use_cosmic_cleaned:
                #for simplicity, using self.filename instead of self.err_filename
                #since will assume err_filename = "e." + self.filename
                base = op.basename(self.filename)
                if base[0] != 'c':
                    path = op.dirname(self.err_filename)

                    cosmic = op.join(path, "e.c" + base)
                    log.info("Attempting to open cosmic cleaned version of file: " + cosmic)
                    c = pyfits.open(cosmic)
        except:
            log.error("could not open file " + cosmic, exc_info=True)
            c = None

        if c is not None:
            self.err_data = np.array(c[0].data)
        else:
            self.err_data = np.array(f[0].data)

        # clean up any NaNs
        self.err_data[np.isnan(self.err_data)] = 0.0

        try:
            f.close()
        except:
            log.error("could not close file " + self.err_filename, exc_info=True)

        if c is not None:
            try:
                c.close()
            except:
                log.error("could not close file cosmic file version of " + self.filename, exc_info=True)

        return

    def read_fefits(self):

        if self.fe_filename is None:
            return None

        try:
            f = pyfits.open(self.fe_filename)
        except:
            log.error("could not open file " + self.fe_filename, exc_info=True)
            return None

        try:
            self.fe_data = np.array(f[0].data)
            # clean up any NaNs
            self.fe_data[np.isnan(self.fe_data)] = 0.0
            self.fe_crval1 = f[0].header['CRVAL1']
            self.fe_cdelt1 = f[0].header['CDELT1']
        except:
            log.error("could not read values or data from file " + self.fe_filename, exc_info=True)

        try:
            f.close()
        except:
            log.error("could not close file " + self.fe_filename, exc_info=True)

        return

    def read_panacea_fits(self):
        #this represents one AMP
        #15 hdus, different header keys

        if not self.filename:
            return None

        if not op.exists(self.filename):
            log.error("Error. FITS file does not exist: " + self.filename)
            return None

        try:
            f = pyfits.open(self.filename)
        except:
            log.error("could not open file " + self.filename, exc_info=True)
            return None

        try:
            #build idx
            #the position of each extention within the multi-frame panacea FITS is not fixed,
            #so need to build the index (dictionary) for each one we load
            hdu_idx = {}
            for i in range(len(f)):
                try:
                    hdu_idx[f[i].header['EXTNAME']] = i
                except:
                    pass

            #use the cleaned image for display
            self.data = np.array(f[hdu_idx['clean_image']].data)
            self.data[np.isnan(self.data)] = 0.0 # clean up any NaNs

            #get error equivalent
            self.err_data = np.array(f[hdu_idx['error']].data)
            self.err_data[np.isnan(self.err_data)] = 0.0

            #get fe equivalent
            self.fe_data = np.array(f[hdu_idx['sky_subtracted']].data)
            self.fe_data[np.isnan(self.fe_data)] = 0.0

            # get fe equivalent (need also the matching wavelengths)
            self.wave_data = np.array(f[hdu_idx['wavelength']].data)
            self.wave_data[np.isnan(self.wave_data)] = 0.0

            self.trace_data = np.array(f[hdu_idx['trace']].data)
            self.trace_data[np.isnan(self.trace_data)] = 0.0

            # get fiber centers
            # the fits representation is backward (with grid x,y: 1,112 and 2,112 (i.e at the top) == fiber 1))
            self.fiber_centers = np.array(f[hdu_idx['ifupos']].data)

            #self.pixflat_data = np.array(f[hdu_idx['flat_image']].data)
            #self.pixflat_data[np.isnan(self.pixflat_data)] = 0.0

            self.panacea = True

            #most complete header in the raw image
            idx = hdu_idx['image']
        except:
            log.error("Cannot read fits header. Missing expected keywords. " + self.filename, exc_info=True)
            self.okay = False
            return

        try:
            self.tel_ra = float(f[idx].header['RA']) * 15.0  # header is in decimal hours
            self.tel_dec = float(f[idx].header['DEC'])  # header is in decimal degs
            self.parangle = f[idx].header['PA']
        except:
            log.error("Non-fatal: Cannot translate RA and/or Dec from FITS format to degrees in " + self.filename, exc_info=True)
            #might be okay, depeding on if the individual emission lines have the weighted RA and Dec Specified

        try:
            self.ifuid = str(f[idx].header['IFUSID']).zfill(3)
            self.ifuslot = str(f[idx].header['IFUSLOT']).zfill(3)
            self.specid = str(f[idx].header['SPECID']).zfill(3)
            self.amp = f[idx].header['AMP']
            self.side = f[idx].header['AMP'][0] #the L or R ... probably don't need this anyway
            #self.exptime = f[idx].header['EXPTIME']
        except:
            log.error("Cannot read fits header. Missing expected keywords. Will attempt to pull from filename." + self.filename, exc_info=True)
            #try to get info from the filename
            self.parse_panacea_fits_name(self.filename)
            return

        try:
            f.close()
        except:
            log.error("could not close file " + self.filename, exc_info=True)

        return

    def parse_panacea_fits_name(self,name):
        if name is not None:
            if "multi_" in name: #multi_037_073_031_LL.fits
                toks = name.split("_")  #multi_fits_basename = "multi_" + self.specid + "_" + self.ifu_slot_id + "_" + self.ifu_id + "_"
                if len(toks) == 5:
                    try:
                        self.specid = toks[1].zfill(3)
                        self.ifuslot = toks[2].zfill(3)
                        self.ifuid = toks[3].zfill(3)
                        self.amp = toks[4][0:2]
                        self.side =toks[4][0]
                    except:
                        log.error("Cannot parse panaces fits filename: %s" %name,exc_info=True)
                        self.okay = False



    def cleanup(self):
        #todo: close fits handles, etc
        pass
