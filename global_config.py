from __future__ import print_function
import logging
import os.path as op
from datetime import datetime
import numpy as np


#from guppy import hpy
#HPY = hpy()
#import gc

#catalogs are defined at top of catalogs.py
import socket
hostname = socket.gethostname()

#version
__version__ = '1.7.5a3'

#python version
import sys
PYTHON_MAJOR_VERSION = sys.version_info[0]
PYTHON_VERSION = sys.version_info
if sys.byteorder == 'big':
    BIG_ENDIAN = True
else:
    BIG_ENDIAN = False

LAUNCH_PDF_VIEWER = None
if hostname != "z50":
    HDR1 = True #set to TRUE for HDR1 release
else:
    HDR1 = False

if HDR1: #set these paths as appropriate for HETDEX DATA RELEASE-1
    #base path: /work/03946/hetdex/hdr1/

    HDF5_DETECT_FN = "/work/03946/hetdex/hdr1/detect/detect_hdr1.h5"
    HDF5_CONTINUUM_FN = "/work/03946/hetdex/hdr1/detect/continuum_sources.h5"
    HDF5_SURVEY_FN = "/work/03946/hetdex/hdr1/survey/survey_hdr1.h5"
    OBSERVATIONS_BASEDIR = "/work/03946/hetdex/hdr1/reduction/"
    BAD_AMP_LIST = "/work/03261/polonius/maverick/catalogs/bad_amp_list.txt"
    #CONFIG_BASEDIR = "/work/03946/hetdex/hdr1/raw"
    CONFIG_BASEDIR = "/work/03946/hetdex/hdr1/software/"
    PANACEA_RED_BASEDIR = "/work/03946/hetdex/hdr1/raw/red1/reductions/"
    PANACEA_RED_BASEDIR_DEFAULT = PANACEA_RED_BASEDIR
    PANACEA_HDF5_BASEDIR = "/work/03946/hetdex/hdr1/reduction/data"

    #todo: the photo-z files are now in in tar ... need to update handling
    CANDELS_EGS_Stefanon_2016_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/candles_egs/EGS"
    EGS_CFHTLS_PATH = "/work/03946/hetdex/hdr1/imaging/candles_egs/CFHTLS"
    CFHTLS_PHOTOZ_CAT = "/work/03946/hetdex/hdr1/imaging/candles_egs/CFHTLS/photozCFHTLS-W3_270912.out"

    EGS_GROTH_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/candles_egs/groth"
    EGS_GROTH_CAT_PATH = "/work/03946/hetdex/hdr1/imaging/candles_egs/groth"  # note: there is no catalog

    #GOODS_N_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/goods_north/GOODSN"
    #GOODS_N_CAT_PATH = GOODS_N_BASE_PATH

    GOODS_N_BASE_PATH = "/work/03564/stevenf/maverick/GOODSN"
    GOODS_N_CAT_PATH = GOODS_N_BASE_PATH

    STACK_COSMOS_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/cosmos/stackCOSMOS/nano/"
    STACK_COSMOS_CAT_PATH = "/work/03946/hetdex/hdr1/imaging/cosmos/stackCOSMOS"
    COSMOS_EXTRA_PATH = "/work/03946/hetdex/hdr1/imaging/cosmos/COSMOS/"

    DECAM_IMAGE_PATH = "/work/03946/hetdex/hdr1/imaging/shela/nano/"
    SHELA_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/shela/nano/"

    SHELA_CAT_PATH = SHELA_BASE_PATH
    SHELA_PHOTO_Z_COMBINED_PATH = "/work/03946/hetdex/hdr1/imaging/shela/SHELA"
    SHELA_PHOTO_Z_MASTER_PATH = "/work/03946/hetdex/hdr1/imaging/shela/SHELA"

    if op.exists("/work/03946/hetdex/hdr2/imaging/hsc"):
        HSC_BASE_PATH = "/work/03946/hetdex/hdr2/imaging/hsc"
        HSC_CAT_PATH = HSC_BASE_PATH + "/cat_tract_patch"
        HSC_IMAGE_PATH = HSC_BASE_PATH + "/image_tract_patch"
    else:
        HSC_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced"
        HSC_CAT_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced/catalog_tracts"
        HSC_IMAGE_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced/images"

    #KPNO_BASE_PATH = "/work/03261/polonius/hetdex/catalogs/KPNO_Mosaic"
    KPNO_BASE_PATH = "/work/03233/jf5007/maverick/KMImaging/"
    KPNO_CAT_PATH = HSC_BASE_PATH
    KPNO_IMAGE_PATH = HSC_BASE_PATH

else:
    if hostname == 'z50':
        LAUNCH_PDF_VIEWER = 'qpdfview'
    if False:
        HDF5_DETECT_FN = "/work/03946/hetdex/hdr1/detect/detect_hdr1.h5"
        HDF5_CONTINUUM_FN = "/work/03946/hetdex/hdr1/detect/continuum_sources.h5"
        HDF5_SURVEY_FN = "/work/03946/hetdex/hdr1/survey/survey_hdr1.h5"

        #OBSERVATIONS_BASEDIR = "/work/03946/hetdex/maverick/"
        OBSERVATIONS_BASEDIR = "/work/03946/hetdex/hdr1/reduction/"
        BAD_AMP_LIST = "/home/dustin/code/python/elixer/bad_amp_list.txt"

        #CONFIG_BASEDIR = "/home/dustin/code/python/elixer/data/config/"

        # #PANACEA_RED_BASEDIR = "/home/dustin/code/python/elixer/data/config/red1/reductions/"
        # CONFIG_BASEDIR = "/work/03946/hetdex/maverick/"
        # PANACEA_RED_BASEDIR = "/work/03946/hetdex/maverick/red1/reductions/"
        # PANACEA_RED_BASEDIR_DEFAULT = PANACEA_RED_BASEDIR
        # #PANACEA_HDF5_BASEDIR = PANACEA_RED_BASEDIR
        # PANACEA_HDF5_BASEDIR = "/home/dustin/code/python/hdf5_learn/cache"

        CONFIG_BASEDIR = "/work/03946/hetdex/hdr1/software/"
        PANACEA_RED_BASEDIR = "/work/03946/hetdex/hdr1/raw/red1/reductions/"
        PANACEA_RED_BASEDIR_DEFAULT = PANACEA_RED_BASEDIR
        PANACEA_HDF5_BASEDIR = "/work/03946/hetdex/hdr1/reduction/data"

        CANDELS_EGS_Stefanon_2016_BASE_PATH = "/home/dustin/code/python/elixer/data/EGS"
        EGS_CFHTLS_PATH = "/home/dustin/code/python/elixer/data/CFHTLS"
        CFHTLS_PHOTOZ_CAT = "/home/dustin/code/python/elixer/data/CFHTLS/photozCFHTLS-W3_270912.out"
        GOODS_N_BASE_PATH = "/home/dustin/code/python/elixer/data/GOODSN/"
        GOODS_N_CAT_PATH = GOODS_N_BASE_PATH

        EGS_GROTH_BASE_PATH = "/home/dustin/code/python/elixer/data/isak"
        EGS_GROTH_CAT_PATH = EGS_GROTH_BASE_PATH #note: there is no catalog

        STACK_COSMOS_BASE_PATH = "/home/dustin/code/python/elixer/data/isak"
        STACK_COSMOS_CAT_PATH = "/home/dustin/code/python/elixer/data/isak"
        COSMOS_EXTRA_PATH = "/home/dustin/code/python/elixer/data/"

        SHELA_BASE_PATH = "/media/dustin/dd/hetdex/data/SHELA" #"/home/dustin/code/python/elixer/data/isak/SHELA"
        DECAM_IMAGE_PATH = SHELA_BASE_PATH#"/media/dustin/dd/hetdex/data/decam/images"
        SHELA_CAT_PATH = "/media/dustin/dd/hetdex/data/SHELA"#"/home/dustin/code/python/elixer/data/isak/SHELA"
        SHELA_PHOTO_Z_COMBINED_PATH = "/home/dustin/code/python/elixer/data/isak/SHELA"
        SHELA_PHOTO_Z_MASTER_PATH = "/home/dustin/code/python/elixer/data/isak/SHELA"

        # 2019-08-06 (mshiro base path inaccessible)
        # HSC_BASE_PATH = "/work/04094/mshiro/maverick/HSC/S15A/reduced"
        # HSC_CAT_PATH = "/media/dustin/dd/hetdex/data/HSC/catalog_tracts" #"/work/04094/mshiro/maverick/HSC/S15A/reduced/catalog_tracts"
        # HSC_IMAGE_PATH = "/work/04094/mshiro/maverick/HSC/S15A/reduced/images"

        if op.exists("/work/03946/hetdex/hdr2/imaging/hsc"):
            HSC_BASE_PATH = "/work/03946/hetdex/hdr2/imaging/hsc"
            HSC_CAT_PATH = HSC_BASE_PATH + "/cat_tract_patch"
            HSC_IMAGE_PATH = HSC_BASE_PATH + "/image_tract_patch"
        else:
            HSC_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced"
            HSC_CAT_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced/catalog_tracts"
            HSC_IMAGE_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced/images"

        DECALS_BASE_PATH = "/media/dustin/dd/hetdex/data/decals"
        DECALS_CAT_PATH = "/media/dustin/dd/hetdex/data/decals"
        DECALS_IMAGE_PATH = "/media/dustin/dd/hetdex/data/decals"

        #KPNO_BASE_PATH = "/work/03261/polonius/hetdex/catalogs/KPNO_Mosaic"
        KPNO_BASE_PATH = "/work/03233/jf5007/maverick/KMImaging/"
        KPNO_CAT_PATH = HSC_BASE_PATH
        KPNO_IMAGE_PATH = HSC_BASE_PATH

    else:

        HDF5_DETECT_FN = "/work/03946/hetdex/hdr1/detect/detect_hdr1.h5"
        HDF5_CONTINUUM_FN = "/work/03946/hetdex/hdr1/detect/continuum_sources.h5"
        HDF5_SURVEY_FN = "/work/03946/hetdex/hdr1/survey/survey_hdr1.h5"
        OBSERVATIONS_BASEDIR = "/work/03946/hetdex/hdr1/reduction/"
        BAD_AMP_LIST = "/work/03261/polonius/maverick/catalogs/bad_amp_list.txt"
        # CONFIG_BASEDIR = "/work/03946/hetdex/hdr1/raw"
        CONFIG_BASEDIR = "/work/03946/hetdex/hdr1/software/"
        PANACEA_RED_BASEDIR = "/work/03946/hetdex/hdr1/raw/red1/reductions/"
        PANACEA_RED_BASEDIR_DEFAULT = PANACEA_RED_BASEDIR
        PANACEA_HDF5_BASEDIR = "/work/03946/hetdex/hdr1/reduction/data"

        # todo: the photo-z files are now in in tar ... need to update handling
        CANDELS_EGS_Stefanon_2016_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/candles_egs/EGS"
        EGS_CFHTLS_PATH = "/work/03946/hetdex/hdr1/imaging/candles_egs/CFHTLS"
        CFHTLS_PHOTOZ_CAT = "/work/03946/hetdex/hdr1/imaging/candles_egs/CFHTLS/photozCFHTLS-W3_270912.out"

        EGS_GROTH_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/candles_egs/groth"
        EGS_GROTH_CAT_PATH = "/work/03946/hetdex/hdr1/imaging/candles_egs/groth"  # note: there is no catalog

        # GOODS_N_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/goods_north/GOODSN"
        # GOODS_N_CAT_PATH = GOODS_N_BASE_PATH

        GOODS_N_BASE_PATH = "/work/03564/stevenf/maverick/GOODSN"
        GOODS_N_CAT_PATH = GOODS_N_BASE_PATH

        STACK_COSMOS_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/cosmos/stackCOSMOS/nano/"
        STACK_COSMOS_CAT_PATH = "/work/03946/hetdex/hdr1/imaging/cosmos/stackCOSMOS"
        COSMOS_EXTRA_PATH = "/work/03946/hetdex/hdr1/imaging/cosmos/COSMOS/"

        DECAM_IMAGE_PATH = "/work/03946/hetdex/hdr1/imaging/shela/nano/"
        SHELA_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/shela/nano/"

        SHELA_CAT_PATH = SHELA_BASE_PATH
        SHELA_PHOTO_Z_COMBINED_PATH = "/work/03946/hetdex/hdr1/imaging/shela/SHELA"
        SHELA_PHOTO_Z_MASTER_PATH = "/work/03946/hetdex/hdr1/imaging/shela/SHELA"

        if op.exists("/work/03946/hetdex/hdr2/imaging/hsc"):
            HSC_BASE_PATH = "/work/03946/hetdex/hdr2/imaging/hsc"
            HSC_CAT_PATH = HSC_BASE_PATH + "/cat_tract_patch"
            HSC_IMAGE_PATH = HSC_BASE_PATH + "/image_tract_patch"
        else:
            HSC_BASE_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced"
            HSC_CAT_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced/catalog_tracts"
            HSC_IMAGE_PATH = "/work/03946/hetdex/hdr1/imaging/hsc/S15A/reduced/images"

        # KPNO_BASE_PATH = "/work/03261/polonius/hetdex/catalogs/KPNO_Mosaic"
        KPNO_BASE_PATH = "/work/03233/jf5007/maverick/KMImaging/"
        KPNO_CAT_PATH = HSC_BASE_PATH
        KPNO_IMAGE_PATH = HSC_BASE_PATH

VIRUS_CONFIG = op.join(CONFIG_BASEDIR,"virus_config")
FPLANE_LOC = op.join(CONFIG_BASEDIR,"virus_config/fplane")
IFUCEN_LOC = op.join(CONFIG_BASEDIR,"virus_config/IFUcen_files")
DIST_LOC = op.join(CONFIG_BASEDIR,"virus_config/DeformerDefaults")
PIXFLT_LOC = op.join(CONFIG_BASEDIR,"virus_config/PixelFlats")

REPORT_ELIXER_MCMC_FIT = False

RELATIVE_PATH_UNIVERSE_CONFIG = "line_classifier/universe.cfg"
RELATIVE_PATH_FLUX_LIM_FN = "line_classifier/Line_flux_limit_5_sigma_baseline.dat"

LOG_LEVEL = logging.DEBUG

##log initialization moved to elixer.py to incorporate --name into filename
# reminder to self ... this is pointless with SLURM given the bash wraper (which does not know about the
# specific dir name and just builds elixer.run ... so leave this here
LOG_FILENAME = "elixer.log"
#loggin intialization moved to elixer.py in parse_commandline as that is the first place we need to log ...
#   if --help, then the logger is not created
#logging.basicConfig(filename=LOG_FILENAME,level=LOG_LEVEL,filemode='w')
#.debug(), .info(), .warning(), .error(), .critical()



#first time we need to log anything


class Global_Logger:
    FIRST_LOG = True

    def __init__(self,id): #id is a string identifier
        self.logger = logging.getLogger(id)
        self.logger.setLevel(LOG_LEVEL)

        # self.fh = logging.FileHandler(LOG_FILENAME,"w")
        # self.fh.setLevel(LOG_LEVEL)
        # self.logger.addHandler(self.fh)

        # self.ch = logging.StreamHandler(sys.stdout)
        # self.ch.setLevel(LOG_LEVEL)
        # self.logger.addHandler(self.ch)
        #logging.basicConfig(filename=LOG_FILENAME, level=LOG_LEVEL, filemode='w')
        #   #don't set the global log level, else imported packages might start logging
        # well that does not quite work ...

        if self.__class__.FIRST_LOG:
            logging.basicConfig(filename=LOG_FILENAME, filemode='w+')
            self.__class__.FIRST_LOG = False
        else:
            logging.basicConfig(filename=LOG_FILENAME, filemode='a')


    def add_time(self,msg):

        #if self.LOGGER_INITIALIZED == False:
        #    logging.basicConfig(filename=LOG_FILENAME, level=LOG_LEVEL, filemode='w')
        #    self.LOGGER_INITIALIZED = True

        try:
            d = datetime.now()
            msg = "[%s:%s:%s.%s]  %s" %(str(d.hour).zfill(2),str(d.minute).zfill(2),str(d.second).zfill(2),
                                        str(d.microsecond).zfill(6),msg)
            return msg
        except:
            return msg


    def setlevel(self,level):
        try:
            self.logger.setLevel(level)
        except:
            print("Exception in logger....")

    def debug(self,msg,exc_info=False):
        try:
            msg = self.add_time(msg)
            self.logger.debug(msg,exc_info=exc_info)
        except:
            print("Exception in logger....")

    def info(self,msg,exc_info=False):
        try:
            msg = self.add_time(msg)
            self.logger.info(msg,exc_info=exc_info)
        except:
            print("Exception in logger....")

    def warning(self,msg,exc_info=False):
        try:
            msg = self.add_time(msg)
            self.logger.warning(msg,exc_info=exc_info)
        except:
            print("Exception in logger....")

    def error(self,msg,exc_info=False):
        try:
            msg = self.add_time(msg)
            self.logger.error(msg,exc_info=exc_info)
        except:
            print("Exception in logger....")

    def critical(self, msg, exc_info=False):
        try:
            msg = self.add_time(msg)
            self.logger.critical(msg, exc_info=exc_info)
        except:
            print("Exception in logger....")


def python2():
    if PYTHON_MAJOR_VERSION == 2:
        return True
    else:
        return False

def getnearpos(array,value):
    idx = (np.abs(array-value)).argmin()
    return idx



LyA_rest = 1216. #A 1215.668 and 1215.674
OII_rest = 3727.

#FLUX_CONVERSION = (1./60)*1e-17
HETDEX_FLUX_BASE_CGS = 1e-17

CONTINUUM_FLOOR_COUNTS = 6.5 #5 sigma * 6 counts / sqrt(40 angstroms/1.9 angs per pixel)

Fiber_Radius = 0.75 #arcsec
IFU_Width = 47.26 #arcsec ... includes 2x fiber radius ... more narrow part fiber 1 - 19, else is 49.8
IFU_Height = 49.98 #arcsec
Fiber_1_X = -22.88
Fiber_1_Y = -24.24
Fiber_19_X = 22.88
Fiber_19_Y = -24.24
Fiber_430_X = -22.88
Fiber_430_Y = 24.24
PreferCosmicCleaned = True #use cosmic cleaned FITS data if available (note: assumes filename is 'c' + filename)

Figure_DPI = 300
FIGURE_SZ_X = 18 #18
#FIGURE_SZ_Y = 9 #12
GRID_SZ_X = 3 # equivalent figure_sz_x for a grid width (e.g. one column)
GRID_SZ_Y = 3 # equivalent figure_sz_y for a grid height (e.g. one row)

LyC = False #switch for Lyman Continuum specialized code
PLOT_FULLWIDTH_2D_SPEC = False #if true, show the combined full-width 2D spectra just under the 1D plot

FIT_FULL_SPEC_IN_WINDOW = False #if true, allow y-axis range to fit entire spectrum, not just the emission line
SHOW_ALL_1D_SPECTRA = False #if true, plot the full width 1D spectra for each hetdex fiber in detection
MAX_COMBINE_BID_TARGETS = 3 #if SINGLE_PAGE_PER_DETECT is true, this is the max number of bid targets that can be
                            #merged on a single line. If the number is greater, each bid target gets its own line

#WARNING! As of version 1.1.10 this should ALWAYS be True ... do not change unless you really
#know what you are doing!!!
SINGLE_PAGE_PER_DETECT = True #if true, a single pdf page per emission line detection is made
FORCE_SINGLE_PAGE = True
SHOW_SKYLINES = True

#1 fiber (the edge-most) fiber
CCD_EDGE_FIBERS_BOTTOM = range(1,20)
CCD_EDGE_FIBERS_TOP = range(439,449)
CCD_EDGE_FIBERS_LEFT = [1,20,40,59,79,98,118,137,157,176,196,215,235,254,274,293,313,332,352,371,391,410,430]
CCD_EDGE_FIBERS_RIGHT = [19,39,58,78,97,117,136,156,175,195,214,234,253,273,292,312,331,351,370,390,409,429,448]
#CCD_EDGE_FIBERS_ALL = list(set(CCD_EDGE_FIBERS_BOTTOM+CCD_EDGE_FIBERS_TOP+CCD_EDGE_FIBERS_LEFT+CCD_EDGE_FIBERS_RIGHT))
CCD_EDGE_FIBERS_ALL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 39, 40, 58, 59, 78,
                         79, 97, 98, 117, 118, 136, 137, 156, 157, 175, 176, 195, 196, 214, 215, 234, 235, 253, 254,
                         273, 274, 292, 293, 312, 313, 331, 332, 351, 352, 370, 371, 390, 391, 409, 410, 429,
                         430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448]

#two fibers from edge
CCD_EDGE_FIBERS_BOTTOM_2 = range(1,40)
CCD_EDGE_FIBERS_TOP_2 = range(410,449)
CCD_EDGE_FIBERS_LEFT_2 = [1,2,20,21,40,41,59,60,79,80,98,99,118,119,137,138,157,158,176,177,196,197,215,216,
                        235,236,254,255,274,275,293,294,313,314,332,333,352,353,371,372,391,392,410,411,430,431]
CCD_EDGE_FIBERS_RIGHT_2 = [18,19,38,39,57,58,77,78,96,97,116,117,135,136,155,156,174,175,194,195,213,214,
                         233,234,252,253,272,273,291,292,311,312,330,331,350,351,369,370,389,390,408,409,428,429,447,448]
#CCD_EDGE_FIBERS_ALL = list(set(CCD_EDGE_FIBERS_BOTTOM+CCD_EDGE_FIBERS_TOP+CCD_EDGE_FIBERS_LEFT+CCD_EDGE_FIBERS_RIGHT))
CCD_EDGE_FIBERS_ALL_2 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 57, 58, 59, 60, 77, 78, 79, 80, 96, 97, 98, 99, 116, 117,
 118, 119, 135, 136, 137, 138, 155, 156, 157, 158, 174, 175, 176, 177, 194, 195, 196, 197, 213, 214, 215, 216, 233, 234,
 235, 236, 252, 253, 254, 255, 272, 273, 274, 275, 291, 292, 293, 294, 311, 312, 313, 314, 330, 331, 332, 333, 350, 351,
 352, 353, 369, 370, 371, 372, 389, 390, 391, 392, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421,
 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445,
 446, 447, 448]

CALFIB_WAVEGRID = np.arange(3470.,5542.,2.0) #3470 - 5540

#Detection Quality Score Values
FULL_WEIGHT_DISTANCE = Fiber_Radius
ZERO_WEIGHT_DISTANCE = 4.0 * Fiber_Radius
COMPUTE_QUALITY_SCORE = False

#quadratic constants for ax^2 + bx + c for fitted quadratic to weight fall off
#QUAD_A = -1/(Fiber_Radius**2*(FULL_WEIGHT_MULT-ZERO_WEIGHT_MULT)**2)
#QUAD_B = 2*FULL_WEIGHT_MULT/(Fiber_Radius*(FULL_WEIGHT_MULT-ZERO_WEIGHT_MULT)**2)
#QUAD_C = (ZERO_WEIGHT_MULT**2-2*FULL_WEIGHT_MULT*ZERO_WEIGHT_MULT)/((FULL_WEIGHT_MULT-ZERO_WEIGHT_MULT)**2)

QUAD_A = -1/(FULL_WEIGHT_DISTANCE-ZERO_WEIGHT_DISTANCE)**2
QUAD_B = 2*FULL_WEIGHT_DISTANCE/(FULL_WEIGHT_DISTANCE-ZERO_WEIGHT_DISTANCE)**2
QUAD_C = (ZERO_WEIGHT_DISTANCE**2-2*FULL_WEIGHT_DISTANCE*ZERO_WEIGHT_DISTANCE)/((FULL_WEIGHT_DISTANCE-ZERO_WEIGHT_DISTANCE)**2)
PLOT_GAUSSIAN = True

ZOO = False #target output for Zooniverse
ZOO_CUTOUTS = False #produce the small zooniverse cutouts
ZOO_MINI = False

UNIQUE_DET_ID_NUM = 0

FLUX_WAVEBIN_WIDTH = 2.0 # AA
NEGATIVE_Z_ERROR = -0.001 #if compuated z is negative, but greater than this, assume == 0.0

CLASSIFY_WITH_OTHER_LINES = True
SPEC_MAX_OFFSET_SPREAD = 2.75 #AA #maximum spread in (velocity) offset (but in AA) across all lines in a solution
MIN_MCMC_SNR = 0.0 #minium SNR from an MCMC fit to accept as a real line (if 0.0, do not MCMC additional lines)
MIN_ADDL_EMIS_LINES_FOR_CLASSIFY = 1

DISPLAY_ABSORPTION_LINES = False
MAX_SCORE_ABSORPTION_LINES = 0.0 #the most an absorption line can contribute to the score (set to 0 to turn off)

MULTILINE_MIN_GOOD_ABOVE_NOISE = 4.0 #below this is not consider a possibly good line
MULTILINE_SCORE_NORM_ABOVE_NOISE = 5.0 #get full 1x score at this level
MULTILINE_SCORE_ABOVE_NOISE_MAX_BONUS = 3.0 #maximum multiplier as max of (peak/noise/NORM, BONUS)
MULTILINE_MIN_SOLUTION_SCORE = 25.0 #remember, this does NOT include the main line's score (about p(noise) = 0.01)
MULTILINE_MIN_SOLUTION_CONFIDENCE = 0.99
MULTILINE_MIN_WEAK_SOLUTION_CONFIDENCE = 0.5
MULTILINE_MAX_PROB_NOISE_TO_PLOT = 0.2 #plot dashed line on spectrum if p(noise) < 0.1
MULTILINE_ALWAYS_SHOW_BEST_GUESS = True #if true, show the best guess even if it does not meet the miniumum requirements
ADDL_LINE_SCORE_BONUS = 5.0 #add for each line at 2+ lines (so 1st line adds nothing)
                            #this is rather "hand-wavy" but gives a nod to having more lines beyond just their score
SHADE_1D_SPEC_PEAKS = False #if true, shade in red the 1D spec peaks above the NORM noise limit (see below)


DYNAMIC_MAG_APERTURE = False  #allow aperture size to change to fit maximum magnitude
MIN_DYNAMIC_MAG_RADIUS = 1.0 #in arcsec
FIXED_MAG_APERTURE = 1.5 #radius in arcsec
MAX_DYNAMIC_MAG_APERTURE = 2.0 #maximum growth in dynamic mag
NUDGE_MAG_APERTURE_CENTER = 0.0  #allow the center of the mag aperture to drift to the 2D Gaussian centroid
                                 #up to this distance in x and y in arcsec (if 0.0 then no drift is allowed)
MAX_SKY_SUBTRACT_MAG = 2.0 #if local sky subtraction results in a magnitude change greater than this value, do not apply it

DEBUG_SHOW_GAUSS_PLOTS = False #set on command line now --gaussplots (but keep here for compatibility with other programs)
MARK_PIXEL_FLAT_CENTER = False

MAX_ANNULUS_RADIUS = 3600.0 #ridiculously large ... need to trim this to a reasonable size
ANNULUS_FIGURE_SZ_X = 12
ANNULUS_FIGURE_SZ_Y = 12

SKY_ANNULUS_MIN_MAG = 15.0 #measure magnitude must be fainter than this to trigger sky subtraction from surrounding annulus

INCLUDE_ALL_AMPS = True #ie. if true, ignore the bad amp list

RECOVERY_RUN = False

ALLOW_EMPTY_IMAGE = False #do not return cutout if it is empty or a simple gradient (essentially, if it has no data)
#note: Pan-STARRS is prioritized over SDSS (since Pan-STARRS is deeper 23.3 vs 22.0)
PANSTARRS_ALLOW = True #if no other catalogs match, try Pan-STARRS as online query (default if not dispatch mode)
PANSTARRS_FORCE = False  #ignore local catalogs and Force the use of only Pan-STARRS

SDSS_ALLOW = True #if no other catalogs match, try SDSS as online query (default if not dispatch mode)
SDSS_FORCE = False  #ignore local catalogs and Force the use of only SDSS

USE_PHOTO_CATS = True  #default normal is True .... use photometry catalogs (if False only generate the top (HETDEX) part)

MAX_NEIGHBORS_IN_MAP = 25

BUILD_HDF5_CATALOG = True