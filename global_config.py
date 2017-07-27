from __future__ import print_function
import logging
import gc

#catalogs are defined at top of catalogs.py
import socket

#version
__version__ = '1.1.0'


if socket.gethostname() == 'z50':
#if False:
    OBSERVATIONS_BASEDIR = "/work/03946/hetdex/maverick/"

    #CONFIG_BASEDIR = "/home/dustin/code/python/voltron/data/config/"
    #PANACEA_RED_BASEDIR = "/home/dustin/code/python/voltron/data/config/red1/reductions/"
    CONFIG_BASEDIR = "/work/03946/hetdex/maverick/"
    PANACEA_RED_BASEDIR = "/work/03946/hetdex/maverick/red1/reductions/"

    CANDELS_EGS_Stefanon_2016_BASE_PATH = "/home/dustin/code/python/voltron/data/EGS"
    GOODS_N_BASE_PATH = "/home/dustin/code/python/voltron/data/GOODSN"
    GOODS_N_CAT_PATH = GOODS_N_BASE_PATH

    EGS_GROTH_BASE_PATH = "/home/dustin/code/python/voltron/data/isak"
    EGS_GROTH_CAT_PATH = EGS_GROTH_BASE_PATH #note: there is no catalog

    STACK_COSMOS_BASE_PATH = "/home/dustin/code/python/voltron/data/isak"
    STACK_COSMOS_CAT_PATH = "/home/dustin/code/python/voltron/data/isak"

    SHELA_BASE_PATH = "/home/dustin/code/python/voltron/data/isak/SHELA"
    SHELA_CAT_PATH = SHELA_BASE_PATH
    SHELA_PHOTO_Z_COMBINED_PATH = SHELA_BASE_PATH
    SHELA_PHOTO_Z_MASTER_PATH = SHELA_BASE_PATH

else:
    OBSERVATIONS_BASEDIR = "/work/03946/hetdex/maverick/"
    CONFIG_BASEDIR = "/work/03946/hetdex/maverick/"
    PANACEA_RED_BASEDIR = "/work/03946/hetdex/maverick/red1/reductions/"

    CANDELS_EGS_Stefanon_2016_BASE_PATH = "/work/03564/stevenf/maverick/EGS"
    GOODS_N_BASE_PATH = "/work/03564/stevenf/maverick/GOODSN"
    GOODS_N_CAT_PATH = GOODS_N_BASE_PATH

    EGS_GROTH_BASE_PATH = "/work/03229/iwold/maverick/groth"
    EGS_GROTH_CAT_PATH = "/work/03229/iwold/maverick/groth" #note: there is no catalog

    STACK_COSMOS_BASE_PATH = "/work/03229/iwold/maverick/stackCOSMOS/nano/"
    STACK_COSMOS_CAT_PATH = "/work/03229/iwold/maverick/stackCOSMOS"

    SHELA_BASE_PATH = "/work/03229/iwold/maverick/fall_field/stack/v2/psf/nano/"
    SHELA_CAT_PATH = SHELA_BASE_PATH
    SHELA_PHOTO_Z_COMBINED_PATH = "/work/03565/stevans/maverick/software/eazy-photoz/inputs_decam1.1_irac1.5_scaled_vistajk/OUTPUT/"
    SHELA_PHOTO_Z_MASTER_PATH = "/work/03565/stevans/maverick/working/decam/psfmatched2017/per_field/v1.0/final_catalogs/v1.1/combined_irac_v1.5.a/with_vista/"

LOG_LEVEL = logging.DEBUG

##log initialization moved to voltron.py to incorporate --name into filename
# reminder to self ... this is pointless with SLURM given the bash wraper (which does not know about the
# specific dir name and just builds voltron.run ... so leave this here
LOG_FILENAME = "voltron.log"
logging.basicConfig(filename=LOG_FILENAME,level=LOG_LEVEL,filemode='w')
#.debug(), .info(), .warning(), .error(), .critical()

LyA_rest = 1216. #A 1215.668 and 1215.674
OII_rest = 3727.

FLUX_CONVERSION = (1./60)*1e-17

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

SHOW_FULL_2D_SPECTRA = False #if true, plot the full width 2D spectra for each hetdex fiber in detection
SINGLE_PAGE_PER_DETECT = True #if true, a single pdf page per emission line detection is made
MAX_COMBINE_BID_TARGETS = 3 #if SINGLE_PAGE_PER_DETECT is true, this is the max number of bid targets that can be
                            #merged on a single line. If the number is greater, each bid target gets its own line

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