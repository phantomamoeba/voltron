import global_config as G
import numpy as np
import tables

from astropy.io import fits as pyfits
from astropy.coordinates import Angle
import os.path as op

#log = G.logging.getLogger('hetdex_logger')
#log.setLevel(G.logging.DEBUG)
log = G.Global_Logger('hetdex_logger')
log.setlevel(G.logging.DEBUG)

class HetdexFits:
    '''A single HETDEX fits file ... 2D spectra, expected to be science file'''

    #needs open with basic validation
    #

    def __init__(self,fn=None,e_fn=None,fe_fn=None,dither_index=-1,panacea=False,hdf5=False,empty=False):
        """

        empty ... if True, don't attempt to read and populate, just return an empty HetdexFits
        """

        self.okay = True
        self.filename = fn
        self.err_filename = e_fn
        self.fe_filename = fe_fn

        self.panacea = panacea
        self.hdf5 = hdf5

        # if HDF5, this must be a panacea style
        # since the panacea flag is used elsewhere and this is decoupled from the actual FITS format
        #    set the panasea flag to True
        if hdf5:
            self.panacea = True

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
        self.data_sky = None #sky NOT subtracted
        self.err_data = None
        self.fe_data = None #fiber extracted counts
        self.wave_data = None #matched wavelengths
        self.trace_data = None
        self.fiber_to_fiber = None
        self.error_analysis = None
        self.pixflat_data = None
        self.fiber_centers = None
        self.fe_crval1 = None
        self.fe_cdelt1 = None

        self.dither_index = dither_index

        self.ampname = None #specifically, Header keyword (or could come from AMPLIFIE)

        #build basic info from filename

        #determine if 'cure'-style fits or panacea fits
        #stupid simple just for now
        #even for annulus, go ahead an read. Don't know if we are going to want the fits files, but may as well get them

        if empty: #don't build this up yet
            return

        if self.hdf5:
            self.read_hdf5()
        elif "multi_" in self.filename: # example: multi_020_095_004_LU.fits
            self.read_panacea_fits()
        else:
            self.read_fits(use_cosmic_cleaned=G.PreferCosmicCleaned)
            self.read_efits(use_cosmic_cleaned=G.PreferCosmicCleaned)
            self.read_fefits()


    def find_hdf5_multifits(self):
         #build up path and see if it exists
        pass


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
            self.ampname = f[idx].header['AMPNAME']
        except:
            log.info("FITS keyword [AMPNAME] not found. Trying alternate [AMPLIFIE] in " + self.filename)
            try:
                self.ampname = f[idx].header['AMPLIFIE']
            except:
                log.info("FITS keyword [AMPLIFIE] not found in " + self.filename)
                self.ampname = None

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

    def read_hdf5(self):

        #todo: debug
        print("******* !!!!!! take this out ... dev only !!!!!!! *******")
        self.filename = "/home/dustin/code/python/hdf5_learn/cache/test_new.h5"

        if not self.filename:
            self.okay = False
            return None

        try:
            with tables.open_file(self.filename, mode="r") as h5_multifits:
                fibers_table = h5_multifits.root.Info.Fibers
                images_table = h5_multifits.root.Info.Images
                shots_table = h5_multifits.root.Info.Shot

                # set the query values needed shortly ...
                # query a specific fiber by ifuid ... amp and fiber_number
                q_specid = str(self.specid).zfill(3)
                # q_ifuid = str(self.ifuid).zfill(3)
                # q_ifuslot = str(self.ifuslot).zfill(3)
                q_expnum = int(self.expid)
                q_amp = self.amp

                #########################################
                #shot info
                #########################################

                #should only be one shot ...
                rows = shots_table.read(0)

                if (rows is None) or (len(rows) != 1):
                    self.okay = False
                    log.error("Problem loading multi-fits HDF5 equivalant. Bad Shot table.")
                    return

                row = rows[0]

                self.tel_ra =  row['ra']   #assuming decimal degrees, but is that true? (was not for FITS header)
                self.tel_dec = row['dec']
                self.parangle = row['pa']

                self.obs_date = row['date']
                self.obs_ymd = row['date']
                self.mjd = row['mjd']
                self.obsid = int(row['obsid'])
                self.expid = int(row['expn'])

                #don't currently need time, pressure, etc

                #########################################
                #Amp info (big images)
                #########################################
                rows = images_table.read_where("(specid==q_specid) & (expnum==q_expnum) & (amp==q_amp)")

                if (rows is None) or (len(rows) != 1):
                    self.okay = False
                    log.error("Problem loading multi-fits HDF5 equivalant. Bad Images table.")
                    return

                row = rows[0]

                # use the cleaned image
                self.data = row['clean_image']
                self.data[np.isnan(self.data)] = 0.0  # clean up any NaNs
                if self.data.shape != (1032, 1032):
                    log.error(
                        "ERROR!! Unexpected data shape for [clean_image]. Expected (1032,1032), got (%d,%d)" % (
                            self.data.shape))

                # get the error
                self.err_data = row['error']
                self.err_data[np.isnan(self.err_data)] = 0.0
                if self.err_data.shape != (1032, 1032):
                    log.error("ERROR!! Unexpected data shape for [error]. Expected (1032,1032), got (%d,%d)"
                              % (self.err_data.shape))
                    self.err_data = np.full(self.data.shape,0.0)

                # with the sky NOT subtracted (the raw image)
                self.data_sky = row['image']
                self.data_sky[np.isnan(self.data_sky)] = 0.0  # clean up any NaNs
                if self.data_sky.shape != (1032, 1032):
                    log.error("ERROR!! Unexpected data shape for [0] (data_sky). Expected (1032,1032), got (%d,%d)"
                          % (self.data_sky.shape))

                #########################################
                #fiber info (and amp, etc)
                #!!! For compatibility with the older organization
                #    this is the image data,etc for a single fiber
                #    There will be redundant data
                #########################################

                #for a given SHOT specid OR ifuid OR ifuslot is unique when compbined with the amp and expsosure
                rows = fibers_table.read_where("(specid==q_specid) & (expnum==q_expnum) & (amp==q_amp)")

                #expect there to be 112 fibers (though maybe fewer if some are dead)
                if (rows is None) or (len(rows) == 0):
                    self.okay = False
                    log.error("Problem loading multi-fits HDF5 equivalant. No fibers for request IFU, AMP, EXP, etc")
                    return

                # todo: maybe build up the arrays, as if they were read from a multi-fits file?
                # that is, for each row, starting with index 0, build up the equivalent arrays for:
                # sky_subtracted  (fe_data)  112,1032
                # wavelength (wave_data) 112,1032
                # trace (trace_data) 112,1032
                # fiber_to_fiber (fiber_to_fiber) 112,1032
                # error_analysis (error_analysis) 3,1032  ???
                #
                # this way, all the downstream code stays the same, even if this is duplicate data
                # (and, as a future todo: re-organize the code so this is not necessary)

                self.fe_data = np.zeros((112,1032))
                self.wave_data = np.zeros((112, 1032))
                self.trace_data = np.zeros((112, 1032))
                self.fiber_to_fiber = np.zeros((112, 1032))

                #todo: figure out what to do with error analysis
                #self.error_analysis = np.zeros((3, 1032))

                for row in rows:
                    idx = row['fibnum']

                    self.fe_data[idx] = row['sky_subtracted']
                    self.wave_data[idx] = row['wavelength']
                    self.trace_data[idx] = row['trace']
                    self.fiber_to_fiber[idx] = row['fiber_to_fiber']


                #todo: deal with AMP vs AMPNAME (for flip_amp() ... the pixel flats issue)
                # self.ampname
                #
                # try:
                #     self.ampname = f[idx].header['AMPNAME']
                # except:
                #     log.info("FITS keyword [AMPNAME] not found. Trying alternate [AMPLIFIE] in " + self.filename)
                #     try:
                #         self.ampname = f[idx].header['AMPLIFIE']
                #     except:
                #         log.info("FITS keyword [AMPLIFIE] not found in " + self.filename)
                #         self.ampname = None




        except:
            log.error("Could not process HDF5 multi-fits equivalent: %s" %(self.filename),exc_info=True)
            self.okay = False
            return None

    def read_panacea_fits(self):
        #this represents one AMP
        #15+ hdus, different header keys

        if not self.filename:
            self.okay = False
            return None

        tarfile = None
        file = None
        if not op.exists(self.filename):
            # todo: try to find .tar file and load that way
            log.info("%s does not exist. Looking for tar file ..." %(self.filename))
            tar_fn = self.filename.split("/exp")[0] + ".tar"
            fits_fn = ""

            try:
                if op.exists(tar_fn):
                    if tar.is_tarfile(tar_fn):
                        tarfile = tar.open(name=tar_fn)

                    #search for name first? or just try to extract it ... just extract ... if not there it will throw
                    #an exception and it will be trapped
                    #todo: if the naming of the path becomes irregular
                    #todo: then substring search for the "exp01/virus/multi_xxx.fits" part (should still be exactly one match)
                    #todo: and return the entire string in which it matches as the fits_fn
                    #fqdn = tarfile.getnames()  # list of all conents (as full paths) includes directories

                    # remember, no leading '/' in tarfile contents
                    # fits_fn = "exp" + self.filename.split("/exp")[1]
                    # i.e. = "exp01/virus/multi_038_096_014_RU.fits"

                    fits_fn = "virus" + self.filename.split("/virus/virus")[1]
                    # ie. = "virus0000001/exp01/virus/multi_038_096_014_RU.fits"

                    file = tarfile.extractfile(fits_fn)
                    # remember do not close the tarfile until we are done
                else:
                    log.info("Could not open tarfile:fits (%s: %s)" %(tar_fn,fits_fn))

            except:
                log.error("Error. Could not open tarfile:fits (%s: %s)" %(tar_fn,fits_fn), exc_info=True)
                tarfile = None
                file=None

            if file == None:
                log.error("Error. FITS file does not exist: " + self.filename)
                try:
                    if tarfile:
                        tarfile.close()
                except:
                    log.error("could not close tar file ", exc_info=True)

                return None
        else:
            file = self.filename

        try:
            log.info("Loading %s ..." %self.filename)
            f = pyfits.open(file) #file maybe a file name or a .tar file object
        except:
            log.error("could not open file " + self.filename, exc_info=True)

            try:
                if tarfile:
                    tarfile.close()
            except:
                log.error("could not close tar file ", exc_info=True)
            return None

        try:
            #build idx
            #the position of each extention within the multi-frame panacea FITS is not fixed,
            #so need to build the index (dictionary) for each one we load
            hdu_idx = {}
            for i in range(len(f)):
                try:
                    if f[i].header['EXTNAME'] in hdu_idx:
                        log.warning("WARNING! Duplicate frame 'EXTNAME' found. ['%s'] at index %d and %d in file: %s"
                                    %(f[i].header['EXTNAME'],hdu_idx[f[i].header['EXTNAME']], i,self.filename))
                    else:
                        hdu_idx[f[i].header['EXTNAME']] = i
                except:
                    pass

            #use the cleaned image for display
            self.data = np.array(f[hdu_idx['clean_image']].data)
            self.data[np.isnan(self.data)] = 0.0 # clean up any NaNs

            if self.data.shape != (1032,1032):
                log.error("ERROR!! Unexpected data shape for [clean_image]. Expected (1032,1032), got (%d,%d)" %(self.data.shape))

            #with the sky NOT subtracted
            try:
                self.data_sky = np.array(f[0].data)
                self.data_sky[np.isnan(self.data_sky)] = 0.0  # clean up any NaNs
            except: #error, but not fatal, just keep going
                log.error("Could not load sky NOT subtracted fits data from multi*fits")

            if self.data_sky.shape != (1032,1032):
                log.error("ERROR!! Unexpected data shape for [0] (data_sky). Expected (1032,1032), got (%d,%d)"
                            %(self.data_sky.shape))


            #get error equivalent
            self.err_data = np.array(f[hdu_idx['error']].data)
            if self.err_data.shape != (1032, 1032):
                print("TEMPORARY!!! using [1] for ['error'] frame until name correctd.")
                self.err_data = np.array(f[1].data)

            self.err_data[np.isnan(self.err_data)] = 0.0
            if self.err_data.shape != (1032,1032):
                log.error("ERROR!! Unexpected data shape for [error]. Expected (1032,1032), got (%d,%d)"
                            %(self.err_data.shape))

            #get fe equivalent
            self.fe_data = np.array(f[hdu_idx['sky_subtracted']].data)
            self.fe_data[np.isnan(self.fe_data)] = 0.0
            if self.fe_data.shape != (112,1032):
                log.error("ERROR!! Unexpected data shape for [sky_subtracted]. Expected (112,1032), got (%d,%d)"
                            %(self.fe_data.shape))

            # get fe equivalent (need also the matching wavelengths)
            self.wave_data = np.array(f[hdu_idx['wavelength']].data)
            self.wave_data[np.isnan(self.wave_data)] = 0.0
            if self.wave_data.shape != (112,1032):
                log.error("ERROR!! Unexpected data shape for [wavelength]. Expected (112,1032), got (%d,%d)"
                            %(self.wave_data.shape))

            self.trace_data = np.array(f[hdu_idx['trace']].data)
            self.trace_data[np.isnan(self.trace_data)] = 0.0
            if self.trace_data.shape != (112,1032):
                log.error("ERROR!! Unexpected data shape for [trace]. Expected (112,1032), got (%d,%d)"
                            %(self.trace_data.shape))

            self.fiber_to_fiber = np.array(f[hdu_idx['fiber_to_fiber']].data)
            self.fiber_to_fiber[np.isnan(self.fiber_to_fiber)]
            if self.fiber_to_fiber.shape != (112,1032):
                log.error("ERROR!! Unexpected data shape for [fiber_to_fiber]. Expected (112,1032), got (%d,%d)"
                            %(self.fiber_to_fiber.shape))

            #[0] = wavelength, [1] = empirical? [2] = expected or estimated?
            self.error_analysis = np.array(f[hdu_idx['error_analysis']].data)
            self.error_analysis[np.isnan(self.error_analysis)]
            if self.error_analysis.shape != (3,512):
                log.error("ERROR!! Unexpected data shape for [error_analysis]. Expected (3,512), got (%d,%d)"
                            %(self.error_analysis.shape))

            #note: (this is done by IFU in build_fibers for each fiber that is constructed)
            #closest thing to error is the error_analysis * fiber_to_fiber (for the fiber in question)
            #take spectra ("clean image") and divide by fiber_to_fiber for the fiber in question
            #note fiber to fiber is the deviation from the average of fibers
            #when getting the data for a fiber, need to interpolate the error_analysis to be on same grid
            #      as the wave_data for that fiber and then do the multiply and divide as needed


            # get fiber centers
            # the fits representation is backward (with grid x,y: 1,112 and 2,112 (i.e at the top) == fiber 1))
            self.fiber_centers = np.array(f[hdu_idx['ifupos']].data)
            if self.fiber_centers.shape != (112, 2):
                log.error("ERROR!! Unexpected data shape for [ifupos]. Expected (112,2), got (%d,%d)"
                            % (self.fiber_centers.shape))

            #self.pixflat_data = np.array(f[hdu_idx['flat_image']].data)
            #self.pixflat_data[np.isnan(self.pixflat_data)] = 0.0

            self.panacea = True

            #most complete header in the raw image
            #todo: at some point in late 2017, the 'image' header was dropped ... as this becomes common,
            #todo: should stop trying to read the 'image' header and just always assume the 0th is PRIMARY?
            #todo:   (is always TRUE ... or at least always after a re-reduction?)
            try:
                idx = hdu_idx['image']
            except:
                log.debug("[image] header not found. Will assume 0th header is the PRIMARY.")
                idx = 0

        except:
            log.error("Cannot read fits header. Missing expected keywords. " + self.filename, exc_info=True)
            self.okay = False
            try:
                if tarfile:
                    tarfile.close()
            except:
                log.error("could not close tar file ", exc_info=True)
            return

        try:
            self.tel_ra = float(f[idx].header['RA']) * 15.0  # header is in decimal hours
            self.tel_dec = float(f[idx].header['DEC'])  # header is in decimal degs
            self.parangle = f[idx].header['PA']
        except:
            log.error("Non-fatal: Cannot translate RA and/or Dec from FITS format to degrees in " + self.filename, exc_info=True)
            #might be okay, depeding on if the individual emission lines have the weighted RA and Dec Specified

        try: #reminder not the same as AMP (LU, RU, LL, LR) ... can be UL, etc ... used in flip_amp() in hetdex
            self.ampname = f[idx].header['AMPNAME']
        except:
            log.info("FITS keyword [AMPNAME] not found. Trying alternate [AMPLIFIE] in " + self.filename)
            try:
                self.ampname = f[idx].header['AMPLIFIE']
            except:
                log.info("FITS keyword [AMPLIFIE] not found in " + self.filename)
                self.ampname = None

        try:
            self.ifuid = str(f[idx].header['IFUSID']).zfill(3)
            self.ifuslot = str(f[idx].header['IFUSLOT']).zfill(3)
            self.specid = str(f[idx].header['SPECID']).zfill(3)
            self.amp = f[idx].header['AMP']
            self.side = f[idx].header['AMP'][0] #the L or R ... probably don't need this anyway
            #self.exptime = f[idx].header['EXPTIME']
        except:
            try:
                if tarfile:
                    tarfile.close()
            except:
                log.error("could not close tar file ", exc_info=True)

            log.error("Cannot read fits header. Missing expected keywords. Will attempt to pull from filename." + self.filename, exc_info=True)
            #try to get info from the filename
            self.parse_panacea_fits_name(self.filename)
            return

        try:
            if tarfile:
                tarfile.close()
        except:
            log.error("could not close tar file ", exc_info=True)

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

