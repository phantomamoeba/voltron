#science image (usually very large) FITS file
#represents overall large image: provides small cutouts for display

#needs:
# image location/filename
# decriptive image name
# catalog name (to match back to catalog?)
# filter name
# wavelength(s) covered

#methods
# load file
# get status
# get cutout (takes ra,dec,error) returns cutout_image (the cutout is just another science image)

import global_config
import numpy as np
from astropy.stats import biweight_midvariance, biweight_location
from astropy.visualization import ZScaleInterval
import astropy.io.fits as fits
from astropy.coordinates import SkyCoord
from astropy.coordinates import match_coordinates_sky
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.wcs.utils import skycoord_to_pixel
from astropy import units as u


log = global_config.logging.getLogger('sciimg_logger')
log.setLevel(global_config.logging.DEBUG)

class science_image():

    def __init__(self, wcs_manual=False):
        self.image_location = None
        self.image_name = None
        self.catalog_name = None
        self.filter_name = None
        self.wavelength_aa_min = 0
        self.wavelength_aa_max = 0

        self.ra_center = 0.0
        self.dec_center = 0.0
        self.fits = None # fits handle
        self.wcs = None
        self.vmin = None
        self.vmax = None
        self.pixel_size = None

    def load_image(self,wcs_manual=False):
        if self.image_location is None:
            return -1

        if self.fits is not None:
            try:
                self.fits.close()
            except:
                log.info("Unable to close fits file.")

        try:
            self.fits = fits.open(self.image_location)
        except:
            log.error("Unable to open science image file: %s" %self.image_location)
            return -1

        if wcs_manual:
            self.build_wcs_manually()
        else:
            try:
                self.wcs = WCS(self.image_location)
            except:
                log.error("Unable to use WCS constructor. Will attempt to build manually.", exc_info=True)
                self.build_wcs_manually()

        try:
            self.pixel_size = np.sqrt(self.wcs.wcs.cd[0, 0] ** 2 + self.wcs.wcs.cd[0, 1] ** 2) * 3600.0  # arcsec/pixel
        except:
            log.error("Unable to build pixel size", exc_info=True)

    def build_wcs_manually(self):
        self.wcs = WCS(naxis=self.fits[0].header['NAXIS'])
        self.wcs.wcs.crpix = [self.fits[0].header['CRPIX1'], self.fits[0].header['CRPIX2']]
        self.wcs.wcs.crval = [self.fits[0].header['CRVAL1'], self.fits[0].header['CRVAL2']]
        self.wcs.wcs.ctype = [self.fits[0].header['CTYPE1'], self.fits[0].header['CTYPE2']]
        #self.wcs.wcs.cdelt = [None,None]#[hdu1[0].header['CDELT1O'],hdu1[0].header['CDELT2O']]
        self.wcs.wcs.cd = [[self.fits[0].header['CD1_1'], self.fits[0].header['CD1_2']],
                           [self.fits[0].header['CD2_1'], self.fits[0].header['CD2_2']]]
        self.wcs._naxis1 = self.fits[0].header['NAXIS1']
        self.wcs._naxis2 = self.fits[0].header['NAXIS2']

    def contains_position(self,ra,dec):
        try:
            cutout = Cutout2D(self.fits[0].data, SkyCoord(ra, dec, unit="deg", frame='fk5'), (1, 1), wcs=self.wcs, copy=True)
        except:
            log.debug("position (%f, %f) is not in image." % (ra,dec), exc_info=True)
            return False
        return True


    def get_vrange(self,vals):
        self.vmin = None
        self.vmax = None

        try:
            zscale = ZScaleInterval(contrast=0.25,krej=2.5) #nsamples=len(vals)
            self.vmin, self.vmax = zscale.get_limits(values=vals )
        except:
            log.info("Exception in science_image::get_vrange:",exc_info =True)

        return self.vmin,self.vmax

    def get_cutout(self,ra,dec,error,window=None):
        '''ra,dec in decimal degrees. error and window in arcsecs'''
        #error is central box (+/- from ra,dec)
        #window is the size of the entire coutout
        #return a new science_image

        if (error is None or error == 0) and (window is None or window == 0):
            log.info("inavlid error box and window box")
            return None

        if window is None or window < error:
            window = max(2*error,5) #should be at least 5 arcsecs

        if not (self.contains_position(ra,dec)):
            log.info("science image does not contain requested position: RA=%f , Dec=%f" %(ra,dec))
            return None

        try:
            position = SkyCoord(ra, dec, unit="deg", frame='fk5')
            window = window / self.pixel_size
            cutout = Cutout2D(self.fits[0].data, position, (window, window), wcs=self.wcs,copy=True)
            self.get_vrange(cutout.data)
        except:
            log.info("Exception in science_image::get_cutout:", exc_info=True)
            return None

        return cutout
