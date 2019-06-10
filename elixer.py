from __future__ import print_function

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt

try:
    from elixer import hetdex
    from elixer import match_summary
    from elixer import global_config as G
    from elixer import catalogs
except:
    import hetdex
    import match_summary
    import global_config as G
    import catalogs


import argparse

from astropy.coordinates import Angle
from matplotlib.backends.backend_pdf import PdfPages
from distutils.version import LooseVersion
import pyhetdex.tools.files.file_tools as ft
import sys
import glob
import os
import fnmatch
import errno
import time
import numpy as np
#import re
#from PIL import Image
from wand.image import Image

import tables



#try:
#    import PyPDF2 as PyPDF
#except ImportError:
#    PyPDF = None

try:
    import elixer.pdfrw as PyPDF
except:
    try:
        import pdfrw as PyPDF
    except ImportError:
        pdfrw = None


VERSION = sys.version.split()[0]
#import random

G_PDF_FILE_NUM = 0

#log = G.logging.getLogger('main_logger')
#log.setLevel(G.logging.DEBUG)
log = G.Global_Logger('main_logger')
log.setlevel(G.logging.DEBUG)

def get_input(prompt):
    if LooseVersion(VERSION) >= LooseVersion('3.0'):
        i = input(prompt)
    else:
        i = raw_input(prompt)
    return i


def parse_astrometry(file):
    ra = None
    dec = None
    par = None
    try:
        with open(file, 'r') as f:
            f = ft.skip_comments(f)
            for l in f:
                if len(l) > 10: #some reasonable minimum
                    toks = l.split()
                    #todo: some sanity checking??
                    ra = float(toks[0])
                    dec = float(toks[1])
                    par = float(toks[2])
    except:
        log.error("Cannot read astrometry file: %s" % file, exc_info=True)

    return ra,dec,par


class PDF_File():
    def __init__(self,basename,id,pdf_name=None):
        self.basename = '%s' % basename
        self.filename = None
        self.id = int(id)
        self.bid_count = 0 #rough number of bid targets included
        if self.id > 0: #i.e. otherwise, just building a single pdf file
            #make the directory
            if not os.path.isdir(self.basename):
                try:
                    os.makedirs(self.basename)
                except OSError as exception:
                    if exception.errno != errno.EEXIST:
                        print ("Fatal. Cannot create pdf output directory: %s" % self.basename)
                        log.critical("Fatal. Cannot create pdf output directory: %s" % self.basename,exc_info=True)
                        exit(-1)
            # have to leave files there ... this is called per internal iteration (not just once0
           # else: #already exists
           #     try: #empty the directory of any previous runs
           #         regex = re.compile(self.filename + '_.*')
           #         [os.remove(os.path.join(self.filename,f)) for f in os.listdir(self.filename) if re.match(regex,f)]
           #     except:
           #         log.error("Unable to clean output directory: " + self.filename,exc_info=True)

            self.filename = None
            if pdf_name is not None:
                #expect the id to be in the pdf_name
                if str(id) in pdf_name:
                    self.filename = os.path.join(self.basename, pdf_name) + ".pdf"

            if self.filename is None:
                if (type(id) == int) or (type(id) == np.int64):
                    if id < 1e9:
                        filename = os.path.basename(self.basename) + "_" + str(id).zfill(3) + ".pdf"
                    else:
                        filename = str(id) + ".pdf"
                else:
                    filename = os.path.basename(self.basename) + "_" + str(id) + ".pdf"

                self.filename = os.path.join(self.basename,filename)
        else:
            pass #keep filename as is

        self.pages = None



def parse_commandline(auto_force=False):
    desc = "(Version %s) Search multiple catalogs for possible object matches.\n\nNote: if (--ra), (--dec), (--par) supplied in " \
           "addition to (--dither),(--line), the supplied RA, Dec, and Parangle will be used instead of the " \
           "TELERA, TELEDEC, and PARANGLE from the science FITS files." % (G.__version__)

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-f', '--force', help='Do not prompt for confirmation.', required=False,
                        action='store_true', default=False)
    parser.add_argument('-c', '--cure', help='Use Cure processed fits (instead of Panacea).', required=False,
                        action='store_true', default=False)

    parser.add_argument('--ra', help='Target RA as decimal degrees or h:m:s.as (end with \'h\')'
                                           'or d:m:s.as (end with \'d\') '
                                           'Examples: --ra 214.963542  or --ra 14:19:51.250h or --ra 214:57:48.7512d'
                                            , required=False)
    parser.add_argument('--dec', help='Target Dec (as decimal degrees or d:m:s.as (end with \'d\') '
                                            'Examples: --dec 52.921167    or  --dec 52:55:16.20d', required=False)
    #parser.add_argument('--rot',help="Rotation (as decimal degrees). NOT THE PARANGLE.",required=False,type=float)
    parser.add_argument('--par', help="The Parangle in decimal degrees.", required=False, type=float)
    parser.add_argument('--rot', help="The rotation in decimal degrees. (Superceeds use of --par)", required=False, type=float)

    parser.add_argument('--ast', help="Astrometry coordinates file. Use instead of --ra, --dec, --par", required=False)

    parser.add_argument('--obsdate', help="Observation Date. Must be YYYYMMDD.  "
                                          "Must provide for Panacea.", required=False)
    parser.add_argument('--obsid', help="Observation ID (integer). "
                                        "Must provide for Panacea.", required=False, type=int)
    parser.add_argument('--specid', help="SpecID aka CAM (integer) i.e. --specid 13 or --specid 13,14,19  "
                                         "If not specified, all are used. (may be restricted by --ifuid or --ifuslot)", required=False, type=int)
    parser.add_argument('--ifuid', help="IFU ID (integer) *** NOTICE. This is the cable ID.  "
                                        "If not specified, all are used (may be restricted by --specid or --ifuslot)", required=False, type=int)
    parser.add_argument('--ifuslot', help="IFU SLOT ID (integer)  "
                                          "If not specified, all are used (may be restricted by --specid or --ifusid)", required=False, type=int)

    parser.add_argument('-e', '--error', help="Error (+/-) in RA and Dec in arcsecs.", required=False, type=float)

    parser.add_argument('--search', help="Search window (+/-) in RA and Dec in arcsecs (for use only with --ra and --dec).", required=False, type=float)

    parser.add_argument('--fibers', help="Number of fibers to plot in 1D spectra cutout."
                                         "If present, also turns off weighted average.", required=False, type=int)

    parser.add_argument('-n','--name', help="Report filename or directory name (if HETDEX emission lines supplied)",required=False)
    parser.add_argument('--multi', help='*Mandatory. Switch remains only for compatibility. Cannot be turned off.*'
                                        'Produce one PDF file per emission line (in folder from --name).', required=False,
                        action='store_true', default=False)

    parser.add_argument('--dither', help="HETDEX Dither file", required=False)
    parser.add_argument('--path', help="Override path to science fits in dither file", required=False)
    parser.add_argument('--line', help="HETDEX detect line file", required=False)
    parser.add_argument('--fcsdir', help="Flux Calibrated Spectra DIRectory (commonly from rsp1). No wildcards. "
                                         "(see --dets)", required=False)
    parser.add_argument('--dets', help="List of detections (of form '20170314v011_005') or subdirs under fscdir "
                        "(wildcards okay) or file containing a list of detections (one per line)", required=False)

    parser.add_argument('--dispatch', help="Dispatched list of directories to process. Auto-created. DO NOT SET MANUALLY",
                        required=False)

    parser.add_argument('--ifu', help="HETDEX IFU (Cure) file", required=False)
    parser.add_argument('--dist', help="HETDEX Distortion (Cure) file base (i.e. do not include trailing _L.dist or _R.dist)",
                        required=False)
    parser.add_argument('--id', help="ID or list of IDs from detect line file for which to search", required=False)
    parser.add_argument('--sigma', help="Minimum sigma threshold (Cure) to meet in selecting detections", required=False,
                        type=float,default=0.0)
    parser.add_argument('--chi2', help="Maximum chi2 threshold (Cure) to meet in selecting detections", required=False,
                        type=float,default=1e9)
    parser.add_argument('--sn', help="Minimum fiber signal/noise threshold (Panacea) to plot in spectra cutouts",
                        required=False, type=float, default=0.0)
    parser.add_argument('--score', help='Do not build report. Just compute detection scores and output *_fib.txt. '
                                        'Currently incompatible with --cure',
                        required=False, action='store_true', default=False)

    parser.add_argument('-t', '--time', help="Max runtime as hh:mm:ss for in SLURM queue",required=False)
    parser.add_argument('--email', help="If populated, sends SLURM status to this email address", required=False)

    parser.add_argument('--queue', help="If populated, specifies which TACC queue (vis, gpu) to use.", required=False)
    parser.add_argument('--tasks', help="If populated, specifies how many TACC tasks to use.", required=False)

    parser.add_argument('--panacea_red',help="Basedir for searching for Panacea reduction files",required=False)

    parser.add_argument('--zoo', help='Produce image cutouts for publication on Zooniverse', required=False,
                        action='store_true', default=False)
    parser.add_argument('--zoox', help='Redact sensitive information AND produce image cutouts for publication on Zooniverse',
                        required=False, action='store_true', default=False)
    parser.add_argument('--jpg', help='Also save report in JPEG format.', required=False,
                        action='store_true', default=False)
    parser.add_argument('--png', help='Also save report in PNG format.', required=False,
                        action='store_true', default=False)
    parser.add_argument('--blind', help='Do not verify passed in detectIDs. Applies only to HDF5 detectIDs.', required=False,
                        action='store_true', default=False)
    parser.add_argument('--allcat', help='Produce individual pages for all catalog matches if there are '
                        'more than 3 matches.', required=False, action='store_true', default=False)

    parser.add_argument('--gaussplots', help='(Debug) output plots of gaussian fits to emission line data',
                        required=False, action='store_true', default=False)
    parser.add_argument('--catcheck', help='Only check to see if there possible matches. Simplified commandline output only',
                        required=False, action='store_true', default=False)

    parser.add_argument('--merge', help='Merge all cat and fib txt files',
                        required=False, action='store_true', default=False)

    parser.add_argument('--annulus', help="Inner and outer radii in arcsec (e.g. (10.0,35.2) )", required=False)
    parser.add_argument('--wavelength', help="Target wavelength (observed) in angstroms for annulus", required=False,
                        type=float)

    parser.add_argument('--include_all_amps', help='Override bad amp list and process all amps',
                        required=False, action='store_true', default=False)

    parser.add_argument('--hdf5', help="HDF5 Detections File (see also --dets)", required=False,
                        default=G.HDF5_DETECT_FN)


    parser.add_argument('--recover', help='Recover/continue from previous run. Will append to and NOT overwrite exsiting output.',
                        required=False, action='store_true', default=False)

    parser.add_argument('--ooops', help='Load Ooops module for SLURM.', required=False,
                        action='store_true', default=False)

    parser.add_argument('--sdss', help="SDSS remote query for imaging. Deny (0), Allow (1) if no other catalog available,"
                                       " Force (2) and override any other catalog",
                        required=False, default=1,type=int)

    parser.add_argument('--nophoto', help='Turn OFF the use of archival photometric catalogs.', required=False,
                        action='store_true', default=False)

    parser.add_argument('--fitspec', help='Adjust y-axis range to accomodate entire sepctrum (not just emission line)', required=False,
                        action='store_true', default=False)

    parser.add_argument('--continuum', help='Use HETDEX continuum catalog instead of the emission line catalog', required=False,
                        action='store_true', default=False)

    #parser.add_argument('--here',help="Do not create a subdirectory. All output goes in the current working directory.",
    #                    required=False, action='store_true', default=False)

    args = parser.parse_args()

    #reminder to self ... this is pointless with SLURM given the bash wraper (which does not know about the
    #speccific dir name and just builds elixer.run

    #if args.name is not None:
    #    G.logging.basicConfig(filename="elixer."+args.name+".log", level=G.LOG_LEVEL, filemode='w')
    #else:
    #    print("Missing mandatory paramater --name.")
    #    exit(-1)

    #regardless of setting, --multi must now always be true
    args.multi = True

    if args.recover:
        G.RECOVERY_RUN = True

    #first time we need to log anything
    G.logging.basicConfig(filename=G.LOG_FILENAME, level=G.LOG_LEVEL, filemode='w')

    log.info(args)

    if auto_force:
        args.force = True #forced to be true in dispatch mode

    if args.merge:
        print("Merging catalogs and fiber files (ignoring all other parameters) ... ")
        return args

    if args.sdss is not None:
        if args.sdss == 0:
            G.SDSS_ALLOW = False
            G.SDSS_FORCE = False
        elif args.sdss == 1:
            G.SDSS_ALLOW = True
            G.SDSS_FORCE = False
        elif args.sdss == 2:
            G.SDSS_ALLOW = True
            G.SDSS_FORCE = True
        else:
            log.warning("Ignoring invalid --sdss value (%d). Using default (Allow == 1)" %args.sdss)
            print("Ignoring invalid --sdss value (%d). Using default (Allow == 1)" %args.sdss)
            G.SDSS_ALLOW = True
            G.SDSS_FORCE = False

    if args.nophoto:
        G.USE_PHOTO_CATS = False

    if args.fitspec:
        G.FIT_FULL_SPEC_IN_WINDOW = True

    if args.continuum:
        args.hdf5 = G.HDF5_CONTINUUM_FN

    if args.annulus:
        try:
            args.annulus = tuple(map(float, args.annulus.translate(None, '( )').split(',')))

            if len(args.annulus)==0:
                print("Fatal. Inavlid annulus.")
                log.error("Fatal. Inavlid annulus.")
                exit(-1)
            elif len(args.annulus)==1: #assume the inner radius is zero
                args.annulus = (0,args.annulus[0])
                log.info("Single valued annulus. Assume 0.0 for the inner radius.")
            elif len(args.annulus) > 2:
                print("Fatal. Inavlid annulus.")
                log.error("Fatal. Inavlid annulus.")
                exit(-1)

            if args.annulus[0] > args.annulus[1]:
                print("Fatal. Inavlid annulus. Inner radius larger than outer.")
                log.error("Fatal. Inavlid annulus. Inner radius larger than outer.")
                exit(-1)

            if (args.annulus[0] < 0) or (args.annulus[1] < 0):
                print("Fatal. Inavlid annulus. Negative value.")
                log.error("Fatal. Inavlid annulus. Negative value.")
                exit(-1)

            if (args.annulus[0] > G.MAX_ANNULUS_RADIUS) or (args.annulus[1] > G.MAX_ANNULUS_RADIUS):
                print("Fatal. Inavlid annulus. Excessively large value.")
                log.error("Fatal. Inavlid annulus. Excessively large value.")
                exit(-1)

        except: #if annulus provided, this is a fatal exception
            print ("Fatal. Failed to map annulus to tuple.")
            log.error("Fatal. Failed to map annulus to tuple.", exc_info=True)
            exit(-1)

    if args.wavelength:
        try:
            if not (3500.0 < args.wavelength < 5500.0):
                print("Fatal. Invalid target wavelength.")
                log.error("Fatal. Invalid target wavelength.")
                exit(-1)
        except:
            print("Fatal. Invalid target wavelength.")
            log.error("Fatal. Invalid target wavelength.")
            exit(-1)

    if args.gaussplots is not None:
        G.DEBUG_SHOW_GAUSS_PLOTS = args.gaussplots

    if (args.allcat is not None):
        G.FORCE_SINGLE_PAGE = not args.allcat

    if (args.zoo is not None) and (args.zoo):
        #G.ZOO = False #for now, don't hide, just do the cutouts
        G.ZOO_CUTOUTS = True

    if (args.zoox is not None) and (args.zoox):
        G.ZOO = True
        G.ZOO_CUTOUTS = True


    if args.dispatch is not None:
        if args.ra is not None: #then this is from selixer and dispatch needs to be the dets list
            args.ra = None
            args.dec = None
            args.dets = args.dispatch

            log.info("Command line: --dets set to --dispatch and ignoring --ra and --dec")

    if args.ra is not None:
        if ":" in args.ra:
            try:
                args.ra = float(Angle(args.ra).degree)
            except:
                print("Error. Cannot determine format of RA")
                log.critical("Main exit. Invalid command line parameters.")
                exit(-1)
        elif args.ra[-1].lower() == 'h': #decimal hours
            args.ra = float(args.ra.rstrip('Hh'))  * 15.0
        elif args.ra[-1].lower() == 'd': #decimal (unncessary)
            args.ra = float(args.ra.rstrip('Dd'))
        else:
            args.ra = float(args.ra)

    if args.dec is not None:
        if ":" in args.dec:
            try:
                args.dec = float(Angle(args.dec).degree)
            except:
                print("Error. Cannot determine format of DEC")
                log.critical("Main exit. Invalid command line parameters.")
                exit(-1)
        elif args.dec[-1].lower() == 'd': #decimal (unncessary)
            args.dec = float(args.dec.rstrip('Dd'))
        else:
            args.dec = float(args.dec)

    if args.ast is not None:
        r,d,p = parse_astrometry(args.ast)
        if r is not None:
            args.ra = r
            args.dec = d
            args.par = p


    if not (args.catcheck or args.annulus):
        if args.error < 0:
            print("Invalid --error. Must be non-negative.")
            log.critical("Main exit. Invalid command line parameters.")
            exit(0)

        if not args.force:
            prompt = ""
            if (args.ra is not None) and (args.dec is not None):
                prompt = "Looking for targets +/- %f\" from RA=%f DEC=%f\nProceed (y/n ENTER=YES)?" \
                              % (args.error, args.ra, args.dec)
            else:
                prompt = "Looking for targets +/- %f\" from detections listed in file.\nProceed (y/n ENTER=YES)?" \
                            % args.error

            i = get_input(prompt)

            if len(i) > 0 and i.upper() !=  "Y":
                print ("Cancelled.")
                log.critical("Main exit. User cancel.")
                exit(0)
            else:
                print()

    if args.include_all_amps:
        G.INCLUDE_ALL_AMPS = True

    if valid_parameters(args):
        return args
    else:
        print("Invalid command line parameters. Cancelled.")
        log.critical("Main exit. Invalid command line parameters.")
        exit(-1)

def valid_parameters(args):

    result = True

    if not (args.catcheck or args.annulus):
        #also check name and error
        if args.name is None:
            print("--name is required")
            result = False

        if args.error is None:
            print("--error is required")
            result = False
    else:
        if args.error is None:
            args.error = 0.0
        if args.name is None:
            args.name = "argscheck"

    if args.search is not None:
        try:
            f = float(args.search)
            if f < 0:
                print("Invalid --search")
                result = False
        except:
            print("Invalid --search")
            result = False

    #must have ra and dec -OR- dither and (ID or (chi2 and sigma))
    if result:
        if (args.ra is None) or (args.dec is None):
            if (args.line is None) and (args.fcsdir is None) and(args.hdf5 is None):
                print("Invalid parameters. Must specify either (--ra and --dec) or detect parameters (--dither, --line, --id, "
                      "--sigma, --chi2, --fcsdir, --hdf5)")
                result =  False
            elif args.cure:
                if (args.ifu is None):
                    print("Warning. IFU file not provided. Report might not contain spectra cutouts. Will search for IFU file "
                          "in the config directory.")
                if (args.dist is None):
                    print("Warning. Distortion file (base) not provided. Report might not contain spectra cutouts. "
                          "Will search for Distortion files in the config directory.")

                #just a warning still return True

    if result and (args.obsdate or args.obsid or args.dither):
        #if you proved obsdata and/or obsid they will be used and you must have all three
        if not (args.obsdate and args.obsid and args.dither):
            msg = "If providing obsdate or obsid you must provide obsdate, obsid, and dither"
            log.error(msg)
            print(msg)
            result = False

    #verify files exist and are not empty (--ast, --dither, --line)
    if result:
        for f in (args.ast,args.dither,args.line):
            if f:
                try:
                    if os.path.exists(f):
                        if os.path.getsize(f) == 0:
                            msg = "Provide file is empty: " + f
                            log.error(msg)
                            print(msg)
                            result = False
                    else:
                        msg  = "Provide file does not exist: " + f
                        log.error(msg)
                        print (msg)
                        result = False
                except:
                    result = False
                    log.error("Exception validating files in commandline.",exc_info=True)
                    print("Exception validating files in commandline. Check log file.")

    if result:
        if args.cure and args.score:
            result = False
            msg = "Incompatible commandline parameters --cure and --score."
            log.error(msg)
            print(msg)


    if result and (args.panacea_red is not None):
        if not os.path.isdir(args.panacea_red):
            result = False
            msg = "Invalid Panacea reduction base directory (--panacea_red ) passed on commandline: "\
                  + args.panacea_red
            log.error(msg)
            print(msg)
        else:
            G.PANACEA_RED_BASEDIR = args.panacea_red

    if args.fcsdir is not None:
        if args.fcsdir[-1] == "/":
            args.fcsdir = args.fcsdir.rstrip("/")
        elif args.fcsdir[-1] == "\\":
            args.fcsdir = args.fcsdir.rstrip("\\")


    return result


def build_hd(args):
    #if (args.dither is not None):
    if (args.line is not None) or (args.fcsdir is not None) or (args.hdf5 is not None):#or (args.id is not None):
            return True

    return False

def build_hetdex_section(pdfname, hetdex, detect_id = 0,pages=None,annulus=False):
    #detection ids are unique (for the single detect_line.dat file we are using)
    if pages is None:
        pages = []
    try:
        if annulus:
            pages = hetdex.build_hetdex_annulus_data_page(pages, detect_id)
        else:
            pages = hetdex.build_hetdex_data_page(pages,detect_id)
    except:
        log.error("Exception calling hetdex.build_hetdex_data_page(): ", exc_info=True)

    if pages is not None:
        if (PyPDF is not None):
            build_report_part(pdfname,pages)
            pages = None

    return pages


def build_pages (pdfname,match,ra,dec,error,cats,pages,num_hits=0,idstring="",base_count = 0,target_w=0,fiber_locs=None,
                 target_flux=None,annulus=None,obs=None):
    #if a report object is passed in, immediately append to it, otherwise, add to the pages list and return that
    section_title = idstring
    count = 0

    log.info("Building page for %s" %pdfname)

    cat_count = 0

    for c in cats:

        if (c is None) or (isinstance(c,list)): #i.e. there are no cats, but it is a list with an empty list
            continue

        if annulus is not None:
            cutout = c.get_stacked_cutout(ra,dec,window=annulus[1])

            #if cutout is not None:
            try:
                r = c.build_annulus_report(obs=obs,cutout=cutout,section_title=section_title)
            #else:
            #    r = None
            except:
                log.error("Exception in elixer::build_pages",exc_info=True)
                r = None

        else:
            try:
                r = c.build_bid_target_reports(match,ra, dec, error,num_hits=num_hits,section_title=section_title,
                                               base_count=base_count,target_w=target_w,fiber_locs=fiber_locs,
                                               target_flux=target_flux)
            except:
                log.error("Exception in elixer::build_pages",exc_info=True)
                r = None
        count = 0
        if r is not None:
            cat_count+= 1
            if (cat_count > 1) and G.SINGLE_PAGE_PER_DETECT:
                print("INFO: More than one catalog matched .... taking top catalog only. Skipping PDF for %s"
                      % c.Name)
            else:
                if PyPDF is not None:
                    build_report_part(pdfname,r)
                else:
                    pages = pages + r
                count = max(0,len(r)-1) #1st page is the target page

    return pages, count


def open_report(report_name):
    return PdfPages(report_name)

def close_report(report):
    if report is not None:
        report.close()

def add_to_report(pages,report):
    if (pages is None) or (len(pages) == 0):
        return

    print("Adding to report ...")
    rows = len(pages)

    try:
        for r in range(rows):
            report.savefig(pages[r])
    except:
        log.error("Exception in elixer::add_to_report: ", exc_info=True)

    return


def build_report(pages,report_name):
    if (pages is None) or (len(pages) == 0):
        return

    print("Finalizing report ...")

    try:

        pdf = PdfPages(report_name)
        rows = len(pages)

        for r in range(rows):
            pdf.savefig(pages[r])

        pdf.close()
        print("File written: " + report_name)
    except:
        log.error("Exception in elixer::build_report: ", exc_info=True)
        try:
            print("PDF FAILURE: " + report_name)
            pdf.close()
        except:
            pass

    return



def build_report_part(report_name,pages):
    if (pages is None) or (len(pages) == 0):
        return

    global G_PDF_FILE_NUM

    G_PDF_FILE_NUM += 1
    part_name = report_name + ".part%s" % (str(G_PDF_FILE_NUM).zfill(4))

    try:
        pdf = PdfPages(part_name)
        rows = len(pages)

        for r in range(rows):
            pdf.savefig(pages[r])

        pdf.close()
    except:
        log.error("Exception in elixer::build_report_part: ", exc_info=True)
        try:
            print("PDF PART FAILURE: " + part_name)
            pdf.close()
        except:
            pass

    return


def join_report_parts(report_name, bid_count=0):

    if PyPDF is None:
        return
    print("Finalizing report ...")

    metadata = PyPDF.IndirectPdfDict(
        Title='Emission Line eXplorer Report',
        Author="HETDEX, Univ. of Texas",
        Keywords='ELiXer Version = ' + G.__version__)

    if G.SINGLE_PAGE_PER_DETECT:
        #part0001 is the hetdex part (usually 2 pages)
        #part0002 is the catalog part (at least 2 pages, but if greater than MAX_COMBINED_BID_TARGETS
        #         then 2 pages + 1 page for each target
        if (True):
#        if (bid_count <= G.MAX_COMBINE_BID_TARGETS):
            log.info("Creating single page report for %s. Bid count = %d" % (report_name, bid_count))
            list_pages = []
            extra_pages = []

            first_page = True

            for i in range(G_PDF_FILE_NUM):
                #use this rather than glob since glob sometimes messes up the ordering
                #and this needs to be in the correct order
                #(though this is a bit ineffecient since we iterate over all the parts every time)
                part_name = report_name+".part%s" % str(i+1).zfill(4)
                if os.path.isfile(part_name):
                    pages = PyPDF.PdfReader(part_name).pages
                    if first_page:
                        first_page = False
                        for p in pages:
                            list_pages.append(p)
                    else: #get the first two, then go single after that
                        for j in range(min(2,len(pages))):
                            list_pages.append(pages[j])

                        # todo: keep all others as individual pages
                        for j in range(2,len(pages)):
                            extra_pages.append(pages[j])

            if len(list_pages) > 0:
                merge_page = PyPDF.PageMerge() + list_pages
            else:
                #there is nothing to merge
                log.info("No pages to merge for " + report_name)
                print("No pages to merge for " + report_name)
                return

            scale = 1.0 #full scale
            y_offset = 0
            #need to count backward ... position 0,0 is the bottom of the page
            #each additional "page" is advanced in y by the y height of the previous "page"
            for i in range(len(merge_page) - 1, -1, -1):
                page = merge_page[i]
                page.scale(scale)
                page.x = 0
                page.y = y_offset
                y_offset = scale* page.box[3] #box is [x0,y0,x_top, y_top]

            if not report_name.endswith(".pdf"):
                report_name += ".pdf"
            writer = PyPDF.PdfWriter(report_name)

            try:
                writer.addPage(merge_page.render())
                writer.trailer.Info = metadata

                # now, add (but don't merge) the other parts
                for p in extra_pages:
                    writer.addPage(p)

                writer.write()
            except:
                log.error("Error writing out pdf: " + report_name, exc_info = True)

        else: #want a single page, but there are just too many sub-pages

            #todo: merge the top 2 pages (the two HETDEX columns and the catalog summary row)

            list_pages = []
            log.info("Single page report not possible for %s. Bid count = %d" %(report_name,bid_count))
            part_num = 0
            list_pages_top2 = []
            list_pages_bottom = []
            for i in range(G_PDF_FILE_NUM):
                # use this rather than glob since glob sometimes messes up the ordering
                # and this needs to be in the correct order
                # (though this is a bit ineffecient since we iterate over all the parts every time)

                part_name = report_name + ".part%s" % str(i + 1).zfill(4)
                if os.path.isfile(part_name):
                    pages = PyPDF.PdfReader(part_name).pages
                    part_num = i + 1
                    for p in pages:
                        list_pages.append(p)
                        if len(list_pages_top2) < 2:
                            list_pages_top2.append(p)
                        else:
                            list_pages_bottom.append(p)
                    break # just merge the first part

            merge_page = PyPDF.PageMerge() + list_pages
            merge_page_top2 = PyPDF.PageMerge() + list_pages_top2

            scale = 1.0  # full scale
            y_offset = 0
            # need to count backward ... position 0,0 is the bottom of the page
            # each additional "page" is advanced in y by the y height of the previous "page"
            for i in range(len(merge_page) - 1, -1, -1):
                page = merge_page[i]
                page.scale(scale)
                page.x = 0
                page.y = y_offset
                y_offset = scale * page.box[3]  # box is [x0,y0,x_top, y_top]

            if not report_name.endswith(".pdf"):
                report_name += ".pdf"
            writer = PyPDF.PdfWriter(report_name)
            writer.addPage(merge_page.render())

            #now, add (but don't merge) the other parts
            for i in range(part_num,G_PDF_FILE_NUM):
                # use this rather than glob since glob sometimes messes up the ordering
                # and this needs to be in the correct order
                # (though this is a bit ineffecient since we iterate over all the parts every time)
                part_name = report_name + ".part%s" % str(i + 1).zfill(4)
                if os.path.isfile(part_name):
                    writer.addpages(PyPDF.PdfReader(part_name).pages)

            writer.trailer.Info = metadata

            try:
                writer.write()
            except:
                log.error("Error writing out pdf: " + report_name, exc_info=True)

    else:
        log.info("Creating multi-page report for %s. Bid count = %d" % (report_name, bid_count))
        writer = PyPDF.PdfWriter()
        #for --multi the file part numbers are unique. Only the first file starts with 001. The second starts with
        #where the first left off
        for i in range(G_PDF_FILE_NUM):
            #use this rather than glob since glob sometimes messes up the ordering
            #and this needs to be in the correct order
            #(though this is a bit ineffecient since we iterate over all the parts every time)
            part_name = report_name+".part%s" % str(i+1).zfill(4)
            if os.path.isfile(part_name):
                writer.addpages(PyPDF.PdfReader(part_name).pages)

        writer.trailer.Info = metadata
        writer.write(report_name)

    print("File written: " + report_name)


def delete_report_parts(report_name):
    for f in glob.glob(report_name+".part*"):
        os.remove(f)

def confirm(hits,force):

    if not force:

        if hits < 0:
            msg = "\n%d total possible matches found (no overlapping catalogs).\nProceed anyway (y/n ENTER=YES)?" % hits
        else:
            msg = "\n%d total possible matches found.\nProceed (y/n ENTER=YES)?" % hits

        i = get_input(msg)

        if len(i) > 0 and i.upper() != "Y":
            print("Cancelled.")
            return False
        else:
            print()
    else:
        print("%d possible matches found. Building report..." % hits)

    return True


def ifulist_from_detect_file(args):
    ifu_list = []
    if args.line is not None:
        try:
            with open(args.line, 'r') as f:
                f = ft.skip_comments(f)
                for l in f:
                    toks = l.split()
                    if len(toks) > 17: #this may be an aggregate line file (last token = ifuxxx)
                        if "ifu" in toks[17]:
                            ifu = str(toks[17][-3:])  # ifu093 -> 093
                            if ifu in ifu_list:
                                continue
                            else:
                                ifu_list.append(ifu)
        except:
            log.info("Exception checking detection file for ifu list", exc_info=True)
    return ifu_list


def write_fibers_file(filename,hd_list):
    if not filename or not hd_list or (len(hd_list) == 0):
        return None

    sep = "\t"

    write_header = True
    if G.RECOVERY_RUN:
        try:
            if os.path.isfile(filename):
                write_header = False
        except:
            log.info("Unexpected exception (not fatal) in elixer::write_fibers_file",exc_info=True)

        try:
            f = open(filename, 'a+') #open for append, but create if it does not exist
        except:
            log.error("Exception create match summary file: %s" % filename, exc_info=True)
            return None
    else: #not a recovery run ... overwrite what is there
        try:
            f = open(filename, 'w')
        except:
            log.error("Exception create match summary file: %s" % filename, exc_info=True)
            return None

    if write_header:
        #write header info
        headers = [
            "fullname / PDF name",
            "input (entry) ID",
            "detect ID",
            #"detection quality score",
            "emission line RA (decimal degrees)",
            "emission line Dec (decimal degrees)",
            "emission line wavelength (AA)",
            #"emission line sky X",
            #"emission line sky Y",
            "emission line sigma (significance) for cure or S/N for panacea",
            "emission line chi2 (point source fit) (cure)",
            "emission line estimated fraction of recovered flux",
            "emission line flux (electron counts)",
            "emission line flux (cgs)",
            "emission line continuum flux (electron counts)",
            "emission line continuum flux (cgs)",
            "emission line equivalent width (observed) [estimated]",
            "P(LAE)/P(OII)",
            "number of fiber records to follow (each consists of the following columns)",
            "  fiber_id string (panacea) or reduced science fits filename (cure)",
            "  observation date YYYYMMDD",
            "  observation ID (for that date)",
            "  exposure ID",
            "  fiber number on full CCD (1-448)",
            "  RA of fiber center",
            "  Dec of fiber center",
            "  X of the fiber center in the IFU",
            "  Y of the fiber center in the IFU",
            "  S/N of emission line in this fiber",
            #"  weighted quality score",
            "  X coord on the CCD for the amp of this emission line in this fiber (as shown in ds9)",
            "  Y coord on the CCD for the amp of this emission line in this fiber (as shown in ds9)",
            "  the next fiber_id string and so on ..."
        ]


        # write help (header) part
        f.write("# version " + str(G.__version__) + "\n")
        f.write("# date time " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n" )
        f.write("# each row contains one emission line with accompanying fiber information\n")
        col_num = 0
        for h in headers:
            col_num += 1
            f.write("# %d %s\n" % (col_num, h))

    #entry_num = 0
    for hd in hd_list:
        for emis in hd.emis_list:
            #entry_num += 1
            #f.write(str(entry_num))
            f.write(str(emis.pdf_name))
            f.write(sep + str(emis.entry_id))
            f.write(sep + str(emis.id))
            #if emis.dqs is None: #as of 1.4.0a11+ not using dqs
            #    emis.dqs_score()
            #f.write(sep + str(emis.dqs))
            if emis.wra:
                f.write(sep + str(emis.wra))
                f.write(sep + str(emis.wdec))
            else:
                f.write(sep + str(emis.ra))
                f.write(sep + str(emis.dec))
            f.write(sep + str(emis.w))

        #dead ... no longer being calculated
           # f.write(sep + str(emis.x))
           # f.write(sep + str(emis.y))

            if emis.snr is not None and emis.snr != 0:
                f.write(sep + str(emis.snr))
            elif emis.sn is not None and emis.sn != 0:
                f.write(sep + str(emis.sn))
            else:
                f.write(sep + str(emis.sigma))

            f.write(sep + str(emis.chi2))
            f.write(sep + str(emis.fluxfrac))
            f.write(sep + str(emis.dataflux))
            f.write(sep + str(emis.estflux))
            f.write(sep + str(emis.cont))
            f.write(sep + str(emis.cont_cgs))
            f.write(sep + str(emis.eqw_obs))
            f.write(sep + str(emis.p_lae_oii_ratio))

            f.write(sep + str(len(emis.fibers)))

            for fib in emis.fibers:
                f.write(sep + str(fib.idstring))
                f.write(sep + str(fib.dither_date))
                f.write(sep + str(fib.obsid))
                f.write(sep + str(fib.expid))
                f.write(sep + str(fib.number_in_ccd))
                f.write(sep + str(fib.ra)) #of fiber center
                f.write(sep + str(fib.dec))
                f.write(sep + str(fib.sky_x)) #of fiber center
                f.write(sep + str(fib.sky_y))
                f.write(sep + str(fib.sn))
                #f.write(sep + str(fib.dqs)) #as of 1.4.0a11 not using dqs
                f.write(sep + str(fib.ds9_x))
                f.write(sep + str(fib.ds9_y))

            f.write("\n")

    msg = "File written: " + filename
    log.info(msg)
    print(msg)


def convert_pdf(filename, resolution=150, jpeg=True, png=False):

    #file might not exist, but this will just trap an execption
    if filename is None:
        return

    try:
        ext = filename[-4:]
        if ext.lower() != ".pdf":
            try:
                log.debug("Invalid filename passed to elixer::convert_pdf(%s)" % filename)
            except:
                return
    except:
        try:
            log.debug("Invalid filename passed to elixer::convert_pdf(%s)" %filename)
        except:
            return


    try:
        #check that the file exists (can be a timing issue on tacc)
        if not os.path.isfile(filename):
            log.info("Error converting (%s) to image type. File not found (may be filesystem lag. Will sleep and retry."
                     %(filename) )
            time.sleep(5.0) #5 sec should be plenty


        # wand.exceptions.PolicyError: not authorized  ....
        #
        # A workaround for now is to simply change the policy in
        #           /etc/ImageMagick-6/policy.xml for PDFs to read :
        # <policy domain="coder" rights="read" pattern="PDF" />


        pages = Image(filename=filename, resolution=resolution)
        for i, page in enumerate(pages.sequence):
            with Image(page) as img:
                img.colorspace = 'rgb'

                if jpeg:
                    img.format = 'jpg'
                    image_name = filename.rstrip(".pdf") + ".jpg"
                    img.save(filename=image_name)
                    print("File written: " + image_name)

                if png:
                    img.format = 'png'
                    image_name = filename.rstrip(".pdf") + ".png"
                    img.save(filename=image_name)
                    print("File written: " + image_name)

    except:
        log.error("Error converting to pdf to image type: " + filename, exc_info=True)
        return



def get_hdf5_detectids_by_coord(hdf5,ra,dec,error):
    """
    Find all detections within +/- error from given ra and dec

    :param ra: decimal degrees
    :param dec:  decimal degress
    :param error:  decimal degrees
    :return:
    """

    detectids = []
    try:
        with tables.open_file(hdf5, mode="r") as h5:
            dtb = h5.root.Detections

            ra1 = ra - error
            ra2 = ra + error
            dec1 = dec - error
            dec2 = dec + error

            rows = dtb.read_where("(ra > ra1) & (ra < ra2) & (dec > dec1) & (dec < dec2)")

            if (rows is not None) and (rows.size > 0):
                detectids = rows['detectid']
                msg = "%d detection records found +/- %g\" from %f, %f" %(rows.size,error*3600.,ra,dec)
                log.info(msg)
                print(msg)
            else:
                msg = "0 detection records found +/- %g\" from %f, %f" % (error * 3600., ra, dec)
                log.info(msg)
                print(msg)


    except:
        log.error("Exception in elixer.py get_hdf5_detectids_by_coord",exc_info=True)

    return detectids

def get_hdf5_detectids_to_process(args):
    """
    returns a list of detectids (Int64) to process

    This is built from the supplied HDF5 detection file and dets list, translated to detectIDs

    :param args:
    :return:
    """

    if args.hdf5 is None:
        return []

    #check that the file exists
    try:
        if not os.path.isfile(args.hdf5):
            msg = "Fatal. Supplied HDF5 file does not exist (%s)" % (args.hdf5)
            print(msg)
            log.error(msg)
            exit(-1)
    except:
        msg = "Fatal. Supplied HDF5 file does not exist (%s)" % (args.hdf5)
        print(msg)
        log.error(msg,exc_info=True)
        exit(-1)

    detectids = []
    detlist = None

    try:

        if args.dispatch is not None:  # from multi-task SLURM only
            try:
                # is this a list or a file
                if os.path.isfile(args.dispatch):
                    if G.python2():
                        detlist = np.genfromtxt(args.dispatch, dtype=None, comments='#', usecols=(0,))
                    else:
                        detlist = np.genfromtxt(args.dispatch, dtype=None, comments='#', usecols=(0,),encoding=None)
                    log.debug("[dispatch] Loaded --dets as file")
                else:
                    detlist = args.dispatch.replace(', ', ',').split(',')  # allow comma or comma-space separation
                    log.debug("[dispatch] Loaded --dets as list")
            except:
                log.error("Exception processing detections (--dispatch) detlist. FATAL. ", exc_info=True)
                print("Exception processing detections (--dispatch) detlist. FATAL.")
                exit(-1)

        elif args.dets is None:
            # maybe an ra and dec ?
            if (args.ra is not None) and (args.dec is not None) and (args.error is not None):
                # args.ra and dec are now guaranteed to be decimal degrees. args.error is in arcsecs

                if args.search is not None:
                    error = args.search
                else:
                    error = args.error

                return get_hdf5_detectids_by_coord(args.hdf5, args.ra, args.dec, error / 3600.)
            else:
                return []

        #dets might be a single value or a list
        if detlist is None:
            try:
                #is this a list or a file
                if os.path.isfile(args.dets):
                    if G.python2():
                        detlist = np.genfromtxt(args.dets, dtype=None,comments='#',usecols=(0,))
                    else:
                        detlist = np.genfromtxt(args.dets, dtype=None, comments='#', usecols=(0,),
                                                encoding=None)
                    detlist_is_file = True
                    log.debug("Loaded --dets as file")
                elif os.path.isfile(os.path.join("..",args.dets)):
                    if G.python2():
                        detlist = np.genfromtxt(os.path.join("..",args.dets), dtype=None, comments='#', usecols=(0,))
                    else:
                        detlist = np.genfromtxt(os.path.join("..", args.dets), dtype=None, comments='#',
                                                usecols=(0,),encoding=None)
                    detlist_is_file = True
                    log.debug("Loaded --dets as ../<file> ")
                else:
                    detlist = args.dets.replace(', ',',').split(',') #allow comma or comma-space separation
                    log.debug("Loaded --dets as list")
            except:
                log.error("Exception processing detections (--dets) detlist. FATAL. ", exc_info=True)
                print("Exception processing detections (--dets) detlist. FATAL.")
                h5.close()
                exit(-1)

        len_detlist = 0
        try:
            len_detlist = len(detlist)  # ok
        except:
            try:
                len_detlist = detlist.size
            except:
                pass

        if len_detlist == 1 and not isinstance(detlist,list):
            # so we get a list of strings, not just a single string and not a list of characters
            detlist = [str(detlist)]

        if args.blind:
            log.info("Blindly accepting detections list")
            return detlist

        h5 = tables.open_file(args.hdf5, mode="r")

        dtb = h5.root.Detections

        #iterate through --dets (might be detectID or some other format ... allow mixed)
        for d in detlist:

            #is it an int?
            #could be a string as an int
            try:
                if str(d).isdigit():
                    #this is a detectid"
                    id = int(d)
                    rows = dtb.read_where("detectid==id")
                    num = rows.size

                    if num == 0:
                        log.info("%d not found in HDF5 detections" %(id))
                        continue
                    elif num == 1:
                        log.info("%d added to detection list" %(id))
                        detectids.append(id)
                        continue
                    else:
                        log.info("%d detectid is not unique" %(id))
                        #might be something else, like 20180123 ??
                        #todo: for now, just skip it ... might consider checking something els
                        continue
            except:
                pass

            #todo: ould be a range: like 123-130 or 123:130 as slices or ranges?

            #is it an old style id ... like "20180123v009_5"
            try:
                if "v" in str(d).lower():

                    if "_" in str(d): #this is a specific input

                        #todo: this could represent a name .... could map to multiple detectIDs
                        #currently called an "inputid"
                        id  = str(d)
                        rows = dtb.read_where("inputid==id")
                        num = rows.size

                        if num == 0:
                            log.info("%s not found in HDF5 detections" % (id))
                            continue
                        elif num == 1:
                            d_id = rows['detectid'][0]
                            log.info("%s added to detection list as %d" % (id,d_id))
                            detectids.append(d_id)
                            continue
                        else:
                            log.info("%s inputid is not unique" % (id))
                            # might be something else, like 20180123 ??
                            # todo: for now, just skip it ... might consider checking something els
                            continue
                    else: #this is just a datevshot, get the entire shot
                        #assumes a 20180123v009 format
                        try:
                            toks = str(d).lower().split('v')
                            q_date = int(toks[0])
                            q_shot = int(toks[0]+toks[1])

                            rows = dtb.read_where("(date==q_date) & (shotid==q_shot)")

                            if rows is not None:
                                for row in rows:
                                    detectids.append(row['detectid'])
                        except:
                            log.error("Invalid detection identifier: %s" %d)

            except:
                pass

        h5.close()

    except:
        msg = "Fatal. Could not consume HDF5 file."
        print(msg)
        log.error(msg,exc_info=True)
        try:
            h5.close()
        except:
            pass
        exit(-1)

    return detectids


def get_fcsdir_subdirs_to_process(args):
#return list of rsp1 style directories to process
    if (args.fcsdir is None) or (args.line is not None): #if a line file was provided, we will use it instead of this
        return []

    fcsdir = args.fcsdir
    detlist_is_file = False
    detlist = [] #list of detections in 20170322v011_005 format
    subdirs = [] #list of specific rsp1 subdirectories to process (output)

    #print(os.getcwd())

    if args.dispatch is not None: #from multi-task SLURM only
        try:
            # is this a list or a file
            if os.path.isfile(args.dispatch):
                if G.python2():
                    detlist = np.genfromtxt(args.dispatch, dtype=None, comments='#', usecols=(0,))
                else:
                    detlist = np.genfromtxt(args.dispatch, dtype=None, comments='#', usecols=(0,),encoding=None)
                log.debug("[dispatch] Loaded --dets as file")
            else:
                detlist = args.dispatch.replace(', ', ',').split(',')  # allow comma or comma-space separation
                log.debug("[dispatch] Loaded --dets as list")
        except:
            log.error("Exception processing detections (--dispatch) detlist. FATAL. ", exc_info=True)
            print("Exception processing detections (--dispatch) detlist. FATAL.")
            exit(-1)

    elif args.dets is not None:
        try:
            #is this a list or a file
            if os.path.isfile(args.dets):
                if G.python2():
                    detlist = np.genfromtxt(args.dets, dtype=None,comments='#',usecols=(0,))
                else:
                    detlist = np.genfromtxt(args.dets, dtype=None, comments='#', usecols=(0,),encoding=None)
                detlist_is_file = True
                log.debug("Loaded --dets as file")
            elif os.path.isfile(os.path.join("..",args.dets)):
                if G.python2():
                    detlist = np.genfromtxt(os.path.join("..",args.dets), dtype=None, comments='#', usecols=(0,))
                else:
                    detlist = np.genfromtxt(os.path.join("..", args.dets), dtype=None, comments='#', usecols=(0,),encoding=None)
                detlist_is_file = True
                log.debug("Loaded --dets as ../<file> ")
            else:
                detlist = args.dets.replace(', ',',').split(',') #allow comma or comma-space separation
                log.debug("Loaded --dets as list")
        except:
            log.error("Exception processing detections (--dets) detlist. FATAL. ", exc_info=True)
            print("Exception processing detections (--dets) detlist. FATAL.")
            exit(-1)

    try:
        if not os.path.isdir(fcsdir):
            log.error("Cannot process flux calibrated spectra directory: " + str(fcsdir))

        #scan subdirs for detections ... assume an rsp1 style format
        #look for "list2" file or "*spec.dat" files

        #pattern = "*spec.dat" #using one of the expected files in subdir not likely to be found elsewhere
        #assumes no naming convention for the directory names or intermediate structure in the tree

        len_detlist = 0
        try:
            len_detlist = len(detlist) #ok
        except:
            try:
                len_detlist = detlist.size
            except:
                pass

        if len_detlist == 1 and not isinstance(detlist,list): #so we get a list of strings, not just a single string and not a list of characters
            detlist = [str(detlist)]

        #if (detlist is None) or (len(detlist) == 0):
        if len_detlist == 0:
            for root, dirs, files in os.walk(fcsdir):
                pattern = os.path.basename(root)+"specf.dat" #ie. 20170322v011_005spec.dat
                for name in files:
                    if name == pattern:
                    #if fnmatch.fnmatch(name, pattern):
                        subdirs.append(root)
                        print("Adding: %s" % root)
                        log.debug("Adding %s" % root)
                        break #stop looking at names in THIS dir and go to next
        else:
            #second check, first version of Karl's headers had no comment
            if detlist[0] == 'name':
                detlist = detlist[1:]

            use_search = False
            log.debug("Attempting FAST search for %d directories ..." %len_detlist)
            #try fast way first (assume detlist is immediate subdirectory name, if that does not work, use slow method
            for d in detlist:

                try:
                    if d[-1] == "/":
                        d = d.rstrip("/")
                except:
                    pass

                if args.annulus:
                    pattern = d + ".spsum"
                else:
                    pattern = d + "specf.dat"
                if os.path.isfile(os.path.join(fcsdir,d,pattern)) or \
                    os.path.isfile(os.path.join(fcsdir, d, os.path.basename(d) + "specf.dat")):
                    subdirs.append(os.path.join(fcsdir,d))
                    log.debug("Adding %s" % os.path.join(fcsdir,d))
                elif os.path.isfile(os.path.join(d,os.path.basename(d)+"specf.dat")):
                    subdirs.append(d)
                    log.debug("Adding %s" % d)
                else:
                    if ("*" in d) or ("?" in d):
                        #this is a wildcard
                        log.debug("Proceeding with wildcard (--fcsdir) search ...")
                    else:
                        log.debug("FAILED to find %s. Will proceed with full search ...." % d)
                        print("*** FAILED: %s" % d) #but keep going

                    #fail, fast method will not work
                    #if any fail, all fail?
                    # log.debug("FAST search fail ... ")
                    # del subdirs[:]
                    # use_search = True
                    # break

            if len(subdirs) == 0:
                log.debug("Fast search method failed. Detlist does not match to subdirectories. Attempting full search...")

                if type(detlist) is str:
                    if '*' in detlist or "?" in detlist:
                        use_search = True
                elif type(detlist) is list:
                    for d in detlist:
                        if '*' in d or "?" in d:
                            use_search = True
                            break

                if use_search:
                    log.debug("Searching fcsdir for matching subdirs ...")
                    if detlist_is_file: #this was a file provided with a list of directories but totally failed, so
                                        #treat like there was no detlist provided at all
                        for root, dirs, files in os.walk(fcsdir):
                            if args.annulus:
                                pattern = os.path.basename(root) + ".spsum"  # ie. 20170322v011_005spec.dat
                            else:
                                pattern = os.path.basename(root) + "specf.dat"  # ie. 20170322v011_005spec.dat
                            for name in files:
                                if name == pattern:
                                    # if fnmatch.fnmatch(name, pattern):
                                    subdirs.append(root)
                                    print("Adding: %s" % root)
                                    log.debug("Adding %s" % root)
                                    break  # stop looking at names in THIS dir and go to next
                    else: #here, detlist was a short command line list or something with wildcards
                        for root, dirs, files in os.walk(fcsdir):
                            #this is a little different in that detlist might be populated with a wildcard pattern
                            if args.annulus:
                                patterns = [x + ".spsum" for x in detlist]  # ie. 20170322v011_005spec.dat
                            else:
                                patterns = [x + "specf.dat" for x in detlist] #ie. 20170322v011_005spec.dat
                            for name in files:
                                #if name in patterns:
                                for p in patterns:
                                    if fnmatch.fnmatch(name, p): #could have wild card
                                        subdirs.append(root)
                                        print("Adding: %s" % root)
                                        log.debug("Adding %s" %root)
                                        break #stop looking at names in THIS dir and go to next
    except:
        log.error("Exception attempting to process --fcsdir. FATAL.",exc_info=True)
        print("Exception attempting to process --fcsdir. FATAL.")
        exit(-1)

    return subdirs


def merge(args=None):
    #must be in directory with all the dispatch_xxx folders
    #for each folder, read in and join the  dispatch_xxx

    #cat file first
    try:
        first = True
        merge_fn = None
        merge = None
        for fn in sorted(glob.glob("dispatch_*/*/*_cat.txt")):
            if first:
                first = False
                merge_fn = os.path.basename(fn)
                merge = open(merge_fn, 'w')

                with open(fn,'r') as f:
                    merge.writelines(l for l in f)
            else:
                with open(fn,'r') as f:
                    merge.writelines(l for l in f if l[0] != '#')

        if merge is not None:
            merge.close()
            print("Done: " + merge_fn)
        else:
            print("No catalog files found. Are you in the directory with the dispatch_* subdirs?")

    except:
        pass

    #fib file
    try:
        first = True
        merge_fn = None
        merge = None
        for fn in sorted(glob.glob("dispatch_*/*/*_fib.txt")):
            if first:
                first = False
                merge_fn = os.path.basename(fn)
                merge = open(merge_fn, 'w')

                with open(fn,'r') as f:
                    merge.writelines(l for l in f)
            else:
                with open(fn,'r') as f:
                    merge.writelines(l for l in f if l[0] != '#')

        if merge is not None:
            merge.close()
            print("Done: " + merge_fn)
        else:
            print("No fiber files found. Are you in the directory with the dispatch_* subdirs?")


    except:
        pass


def prune_detection_list(args,fcsdir_list=None,hdf5_detectid_list=None):
    #find the pdf reports that should correspond to each detction
    #if found that detection is already done, so remove it from the list

    #implement as build a new list ... just easier that way
    if ((fcsdir_list is None) or (len(fcsdir_list) == 0)) and \
            ((hdf5_detectid_list is None) or (len(hdf5_detectid_list) == 0)):
        msg = "Unexpected empty lists. Cannot run in recovery mode."
        log.error(msg)
        print(msg)
        return None

    newlist = []
    if (hdf5_detectid_list is not None) and (len(hdf5_detectid_list) > 0):

        for d in hdf5_detectid_list:
            #does the file exist
            #todo: this should be made common code, so naming is consistent
            filename = str(d)

            if os.path.isfile(os.path.join(args.name, args.name + "_" + filename + ".pdf")) or \
                os.path.isfile(os.path.join(args.name, filename + ".pdf")):
                log.info("Already processed %s. Will skip recovery." %(filename))
            else:
                log.info("Not found (%s). Will process ..." %(filename))
                newlist.append(d)


    else: #this is the fcsdir list

        for d in fcsdir_list:
            filename = os.path.basename(str(d))
            if os.path.isfile(os.path.join(args.name, args.name + "_" + filename + ".pdf")) or \
                os.path.isfile(os.path.join(args.name, filename + ".pdf")):
                log.info("Already processed %s. Will skip recovery." %(filename))
            else:
                log.info("Not found (%s). Will process ..." %(filename))
                newlist.append(d)

    return newlist



def main():

    global G_PDF_FILE_NUM

    #G.gc.enable()
    #G.gc.set_debug(G.gc.DEBUG_LEAK)
    args = parse_commandline()

    if args.merge:
        merge(args)
        exit(0)


    if G.USE_PHOTO_CATS:
        cat_library = catalogs.CatalogLibrary()
        cats = cat_library.get_full_catalog_list()
        catch_all_cat = cat_library.get_catch_all()
        cat_sdss = cat_library.get_sdss()
    else:
        cat_library = []
        cats = []
        catch_all_cat = []
        cat_sdss = []

    pages = []

    #if a --line file was provided ... old way (pre-April 2018)
    #always build ifu_list
    ifu_list = ifulist_from_detect_file(args)

    hd_list = [] #if --line provided, one entry for each amp (or side) and dither
    #for rsp1 variant, hd_list should be one per detection (one per rsp subdirectory) or just one hd object?
    file_list = [] #output pdfs (parts)

    fcsdir_list = []
    hdf5_detectid_list = []

    if args.fcsdir is not None:
        fcsdir_list = get_fcsdir_subdirs_to_process(args) #list of rsp1 style directories to process (each represents one detection)
        if fcsdir_list is not None:
            log.info("Processing %d entries in FCSDIR" %(len(fcsdir_list)))
            print("Processing %d entries in FCSDIR" %(len(fcsdir_list)))

    else:
        hdf5_detectid_list = get_hdf5_detectids_to_process(args)
        if hdf5_detectid_list is not None:
            log.info("Processing %d entries in HDF5" %(len(hdf5_detectid_list)))
            print("Processing %d entries in HDF5" %(len(hdf5_detectid_list)))



    PDF_File(args.name, 1) #use to pre-create the output dir (just toss the returned pdf container)



    #if this is a re-run (recovery run) remove any detections that have already been processed
    master_loop_length = 1
    master_fcsdir_list = []
    master_hdf5_detectid_list = []

    if G.RECOVERY_RUN:
        if len(hdf5_detectid_list) > 0:
            hdf5_detectid_list = prune_detection_list(args,None,hdf5_detectid_list)
            if len(hdf5_detectid_list) == 0:
                print("[RECOVERY MODE] All detections already processed. Exiting...")
                log.info("[RECOVERY MODE] All detections already processed. Exiting...")
                log.critical("Main complete.")
                exit(0)
            else:
                master_loop_length = len(hdf5_detectid_list)
                master_hdf5_detectid_list = hdf5_detectid_list
                log.info("[RECOVERY] Processing %d entries in HDF5" % (len(hdf5_detectid_list)))
                print("[RECOVERY] Processing %d entries in HDF5" % (len(hdf5_detectid_list)))
        elif len(fcsdir_list):
            fcsdir_list = prune_detection_list(args,fcsdir_list,None)
            if len(fcsdir_list) == 0:
                print("[RECOVERY MODE] All detections already processed. Exiting...")
                log.info("[RECOVERY MODE] All detections already processed. Exiting...")
                log.critical("Main complete.")
                exit(0)
            else:
                master_loop_length = len(fcsdir_list)
                master_fcsdir_list = fcsdir_list
                log.info("[RECOVERY] Processing %d entries in FCSDIR" % (len(fcsdir_list)))
                print("[RECOVERY] Processing %d entries in FCSDIR" % (len(fcsdir_list)))
        else:
            G.RECOVERY_RUN = False
            log.debug("No list (hdf5 or fcsdir) of detections, so RECOVERY MODE turned off.")

    #now, we have only the detections that have NOT been processed

    for master_loop_idx in range(master_loop_length):

        #stupid, but works until I can properly reorganize
        #on each run through this loop, set the list to one element
        if len(master_hdf5_detectid_list) > 0: #this is an hdf5 run
            hdf5_detectid_list = [master_hdf5_detectid_list[master_loop_idx]]
        elif len(master_fcsdir_list) > 0:
            fcsdir_list = [master_fcsdir_list[master_loop_idx]]

        #reset the other lists
        del hd_list[:]
        del file_list[:]

        hd_list = []
        file_list = []
        match_list = match_summary.MatchSet()

        # first, if hetdex info provided, build the hetdex part of the report
        # hetedex part
        if build_hd(args):
            #hd_list by IFU (one hd object per IFU, pre-April 2018)
            #each hd object can have multiple DetObjs (assigned s|t the first fiber's IFU matches the hd IFU)
            if (len(ifu_list) > 0) and ((args.ifuslot is None) and (args.ifuid is None) and (args.specid is None)):

                #sort so easier to find
                ifu_list.sort()

                for ifu in ifu_list:
                    args.ifuslot = int(ifu)
                    hd = hetdex.HETDEX(args)
                    if (hd is not None) and (hd.status != -1):
                        hd_list.append(hd)
            elif len(fcsdir_list) > 0: #rsp style
                #build one hd object for each ?
                #assume of form 20170322v011_xxx
                obs_dict = {} #key=20170322v011  values=list of dirs

                for d in fcsdir_list:
                    key = os.path.basename(d).split("_")[0]
                    if key in obs_dict:
                        obs_dict[key].append(d)
                    else:
                        obs_dict[key] = [d]


                for key in obs_dict.keys():
                    plt.close('all')
                    hd = hetdex.HETDEX(args,fcsdir_list=obs_dict[key]) #builds out the hd object (with fibers, DetObj, etc)
                    #todo: maybe join all hd objects that have the same observation
                    # could save in loading catalogs (assuming all from the same observation)?
                    # each with then multiple detections (DetObjs)
                    if hd.status == 0:
                        hd_list.append(hd)
            elif len(hdf5_detectid_list) > 0: #HDF5 (DataRelease style)
                #only one detection per hetdex object
                for d in hdf5_detectid_list:
                    plt.close('all')
                    hd = hetdex.HETDEX(args,fcsdir_list=None,hdf5_detectid_list=[d])

                    if hd.status == 0:
                        hd_list.append(hd)

            else:
                hd = hetdex.HETDEX(args) #builds out the hd object (with fibers, DetObj, etc)
                if hd is not None:
                    if hd.status == 0:
                        hd_list.append(hd)

        if args.score:
            #todo: future possibility that additional analysis needs to be done (beyond basic fiber info). Move as needed
            if len(hd_list) > 0:
                if not os.path.isdir(args.name):
                    try:
                        os.makedirs(args.name)
                    except OSError as exception:
                        if exception.errno != errno.EEXIST:
                            print("Fatal. Cannot create pdf output directory: %s" % args.name)
                            log.critical("Fatal. Cannot create pdf output directory: %s" % args.name, exc_info=True)
                            exit(-1)
                #esp. for older panacea and for cure, need data built in the data_dict to compute score
                for hd in hd_list:
                    for emis in hd.emis_list:
                        emis.outdir = args.name
                        hd.build_data_dict(emis)

                write_fibers_file(os.path.join(args.name, args.name + "_fib.txt"), hd_list)
            log.critical("Main complete.")
            exit(0)

        if len(hd_list) > 0:
            total_emis = 0
            for hd in hd_list:
                if hd.status != 0:
                    if len(hd_list) > 1:
                        continue
                    else:
                        # fatal
                        print("Fatal error. Cannot build HETDEX working object.")
                        log.critical("Fatal error. Cannot build HETDEX working object.")
                        log.critical("Main exit. Fatal error.")
                        exit (-1)

                #iterate over all emission line detections
                if len(hd.emis_list) > 0:
                    total_emis += len(hd.emis_list)
                    print()
                    #first see if there are any possible matches anywhere
                    #matched_cats = []  ... here matched_cats needs to be per each emission line (DetObj)
                    num_hits = 0

                    for e in hd.emis_list:
                        plt.close('all')
                        log.info("Processing catalogs for eid(%s) ... " %str(e.entry_id))

                        if G.SDSS_FORCE:
                            e.matched_cats.append(cat_sdss)
                        else:
                            for c in cats:
                                if (e.wra is not None) and (e.wdec is not None):  # weighted RA and Dec
                                    ra = e.wra
                                    dec = e.wdec
                                else:
                                    ra = e.ra
                                    dec = e.dec
                                if c.position_in_cat(ra=ra, dec=dec, error=args.error): #
                                    in_cat = True
                                    hits, _, _ = c.build_list_of_bid_targets(ra=ra, dec=dec, error=args.error)
                                    if hits < 0:
                                        # detailed examination found that the position cannot be found in the catalogs
                                        # this is for a tiled catalog (like SHELA or HSC) where the range is there, but
                                        # there is no tile that covers that specific position

                                        hits = 0
                                        in_cat = False

                                    num_hits += hits
                                    e.num_hits = hits #yes, for printing ... just the hits in this ONE catalog

                                    if in_cat and (c not in e.matched_cats):
                                        e.matched_cats.append(c)

                                    print("%d hits in %s for Detect ID #%d" % (hits, c.name, e.id))
                                else: #todo: don't bother printing the negative case
                                    print("Coordinates not in range of %s for Detect ID #%d" % (c.name,e.id))

                            if len(e.matched_cats) == 0:
                                if G.SDSS_ALLOW:
                                    e.matched_cats.append(cat_sdss)
                                else:
                                    e.matched_cats.append(catch_all_cat)

                    if (args.annulus is None) and (not confirm(num_hits,args.force)):
                        log.critical("Main exit. User cancel.")
                        exit(0)

                    #now build the report for each emission detection
                    for e in hd.emis_list:
                        pdf = PDF_File(args.name, e.entry_id, e.pdf_name)
                        e.outdir = pdf.basename
                        #update pdf_name to match
                        try:
                            e.pdf_name = os.path.basename(pdf.filename)
                        except:
                            pass #not important if this fails

                        id = "Detect ID #" + str(e.id)
                        if (e.wra is not None) and (e.wdec is not None): #weighted RA and Dec
                            ra = e.wra
                            dec = e.wdec
                        else:
                            ra = e.ra
                            dec = e.dec


                        #todo: ANNULUS STUFF HERE
                        #todo: still use hetdex objects, but want a different hetdex section
                        #todo: and we won't be catalog matching (though will grab images from them)

                        if args.annulus is None:
                            pdf.pages = build_hetdex_section(pdf.filename,hd,e.id,pdf.pages) #this is the fiber, spectra cutouts for this detect

                            match = match_summary.Match(e)

                            pdf.pages,pdf.bid_count = build_pages(pdf.filename, match, ra, dec, args.error, e.matched_cats, pdf.pages,
                                                          num_hits=e.num_hits, idstring=id,base_count=0,target_w=e.w,
                                                          fiber_locs=e.fiber_locs,target_flux=e.estflux)

                            #add in lines and classification info
                            match_list.add(match) #always add even if bids are none
                            file_list.append(pdf)
                        else: #todo: this is an annulus examination (fiber stacking)
                            log.info("***** ANNULUS ***** ")
                            pdf.pages = build_hetdex_section(pdf.filename, hd, e.id, pdf.pages, annulus=True)
                            pdf.pages, pdf.bid_count = build_pages(pdf.filename, None, ra, dec, args.error, e.matched_cats,
                                                                   pdf.pages, num_hits=0, idstring=id, base_count=0,
                                                                   target_w=e.w, fiber_locs=e.fiber_locs,
                                                                   target_flux=e.estflux, annulus=args.annulus,obs=e.syn_obs)
                            file_list.append(pdf)

            # else: #for multi calls (which are common now) this is of no use
               #     print("\nNo emission detections meet minimum criteria for specified IFU. Exiting.\n"
               #     log.warning("No emission detections meet minimum criteria for specified IFU. Exiting.")

            if total_emis < 1:
                log.info("No detections match input parameters.")
                print("No detections match input parameters.")

        elif (args.ra is not None) and (args.dec is not None):
            num_hits = 0
            num_cats = 0
            catlist_str = ""
            matched_cats = [] #there were no detection objects (just an RA, Dec) so use a generic, global matched_cats

            if G.SDSS_FORCE:
                matched_cats.append(cat_sdss)
                catlist_str += cat_sdss.name + ", " #still need this for autoremoval of trailing ", " later
            else:
                for c in cats:
                    if c.position_in_cat(ra=args.ra,dec=args.dec,error=args.error):
                        if args.error > 0:
                            hits,_,_ = c.build_list_of_bid_targets(ra=args.ra,dec=args.dec,error=args.error)

                            if hits < 0:
                                #there was a problem ... usually we are in the footprint
                                #but in a gap or missing area
                                hits = 0
                            else:
                                num_hits += hits
                                num_cats += 1
                                if c not in matched_cats:
                                    matched_cats.append(c)
                                    catlist_str += c.name + ", "

                            if hits > 0:
                                print ("%d hits in %s" %(hits,c.name))
                            elif args.catcheck:
                                print("%d hits in %s (*only checks closest tile)" %(hits,c.name))
                        else:
                            num_cats += 1
                            if c not in matched_cats:
                                matched_cats.append(c)
                                catlist_str += c.name + ", "

                if G.SDSS_ALLOW and (len(matched_cats) == 0):
                    matched_cats.append(cat_sdss)
                    catlist_str += cat_sdss.name + ", " #still need this for autoremoval of trailing ", " later


            if args.catcheck:
                catlist_str = catlist_str[:-2]
                print("%d overlapping catalogs (%f,%f). %s" %(num_cats,args.ra, args.dec, catlist_str))
                exit(0)
                #if num_cats == 0:
                #    num_hits = -1 #will show -1 if no catalogs vs 0 if there are matching catalogs, just no matching targets
                    #print("-1 hits. No overlapping imaging catalogs.")
            else:
                if not confirm(num_hits,args.force):
                    log.critical("Main exit. User cancel.")
                    exit(0)

                pages,_ = build_pages(args.name,None,args.ra, args.dec, args.error, matched_cats, pages, idstring="# 1 of 1")
        else:
            print("Invalid command line call. Insufficient information to execute or No detections meet minimum criteria.")
            exit(-1)

        if len(file_list) > 0:
            for f in file_list:
                build_report(f.pages,f.filename)
        else:
            build_report(pages,args.name)

        if PyPDF is not None:
            if len(file_list) > 0:
                try:
                    for f in file_list:
                        join_report_parts(f.filename,f.bid_count)
                        delete_report_parts(f.filename)
                except:
                    log.error("Joining PDF parts failed for %s" %f.filename,exc_info=True)
            else:
                join_report_parts(args.name)
                delete_report_parts(args.name)

        if match_list.size > 0:
            match_list.write_file(os.path.join(args.name,args.name+"_cat.txt"))

        write_fibers_file(os.path.join(args.name, args.name + "_fib.txt"),hd_list)


        #todo: iterate over detections and make a clean sample for LyC
        #conditions ...
        #   exactly 1 catalog detection
        #   all 3 P(LAE)/P(OII) of similar value (that is all > say, 10)
        #todo: OR - record all in HDF5 and subselect later
        #not an optimal search (lots of redundant hits, but there will only be a few and this is simple to code
        if False:
            for h in hd_list: #iterate over all hetdex detections
                for e in h.emis_list:
                    for c in match_list.match_set: #iterate over all match_list detections
                        if e.id == c.detobj.id: #internal ID (guaranteed unique)

                            print("Detect ID",c.detobj.entry_id)
                            for b in c.bid_targets:
                                print("         ",b.p_lae_oii_ratio,b.distance)
                            print("\n")

                            if False:
                                if len(c.bid_targets) == 2: #the HETDEX + imaging, and 1 catalog match
                                    #c.bid_targets[0] is the hetdex one
                                    #check all plae_poii
                                    if (c.detobj.p_lae_oii_ratio > 10)          and \
                                       (c.bid_targets[0].p_lae_oii_ratio > 10) and \
                                       (c.bid_targets[1].p_lae_oii_ratio > 10):
                                        #meets criteria, so log
                                        if c.bid_targets[1].distance < 1.0:
                                            print(c.detobj.id,c.detobj.p_lae_oii_ratio,c.bid_targets[0].p_lae_oii_ratio,c.bid_targets[1].p_lae_oii_ratio )


                            break





        #temporary
        if args.line:
            try:
                import shutil
                shutil.copy(args.line,os.path.join(args.name,os.path.basename(args.line)))

            except:
                log.error("Exception copying line file: ", exc_info=True)

        if (args.jpg or args.png) and (PyPDF is not None):
            if len(file_list) > 0:
                for f in file_list:
                    try:
                        convert_pdf(f.filename,jpeg=args.jpg, png=args.png)
                    except:
                        log.error("Error converting to pdf to image type: " + f.filename, exc_info=True)
            else:
                try:
                    convert_pdf(args.name,jpeg=args.jpg, png=args.png)
                except:
                    log.error("Error converting to pdf to image type: " + f.filename, exc_info=True)














    log.critical("Main complete.")

    exit(0)

# end main


if __name__ == '__main__':
    main()