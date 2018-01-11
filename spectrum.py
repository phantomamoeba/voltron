import global_config as G
import matplotlib
matplotlib.use('agg')

import matplotlib.pyplot as plt
#from matplotlib.font_manager import FontProperties
#import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import numpy as np
import io
from scipy.stats import gmean
from scipy import signal
from scipy.stats import skew, kurtosis
from scipy.optimize import curve_fit
import copy


log = G.logging.getLogger('spectrum_logger')
log.setLevel(G.logging.DEBUG)

MIN_FWHM = 5
MIN_HEIGHT = 20
MIN_DELTA_HEIGHT = 2 #to be a peak, must be at least this high above next adjacent point to the left
DEFAULT_NOISE = 6.0


#!!!!!!!!!! Note. all widths (like dw, xw, etc are in pixel space, so if we are not using
#!!!!!!!!!!       1 pixel = 1 Angstrom, be sure to adjust


def getnearpos(array,value):
    idx = (np.abs(array-value)).argmin()
    return idx


def gaussian(x,x0,sigma,a=1.0):
    if (x is None) or (x0 is None) or (sigma is None):
        return None
    return a*np.exp(-np.power((x - x0)/sigma, 2.)/2.)


def rms(data, fit):
    #sanity check
    if (data is None) or (fit is None) or (len(data) != len(fit)) or any(np.isnan(data)) or any(np.isnan(fit)):
        return None

    mx = max(data)

    if mx < 0:
        return None

    d = np.array(data)/mx
    f = np.array(fit)/mx

    return np.sqrt(((f - d) ** 2).mean())

def fit_gaussian(x,y):
    yfit = None
    parm = None
    pcov = None
    try:
        parm, pcov = curve_fit(gaussian, x, y,bounds=((-np.inf,0,-np.inf),(np.inf,np.inf,np.inf)))
        yfit = gaussian(x,parm[0],parm[1],parm[2])
    except:
        log.error("Exception fitting gaussian.",exc_info=True)

    return yfit,parm,pcov

def signal_score(wavelengths,values,central,snr=None, show_plot=False):
    wave_step = 1 #pixels
    wave_side = 8 #pixels

    len_array = len(wavelengths)

    idx = getnearpos(wavelengths,central)
    min_idx = max(0,idx-wave_side)
    max_idx = min(len_array,idx+wave_side)
    wave_x = wavelengths[min_idx:max_idx+1]
    wave_counts = values[min_idx:max_idx+1]

    #blunt very negative values
    #wave_counts = np.clip(wave_counts,0.0,np.inf)

    xfit = np.linspace(wave_x[0], wave_x[-1], 100)

    fit_wave = None
    #rms_wave = None
    #error = None
    fit_range = 1.0 #peak must fit to within +/- fit_range pixels

    #use ONLY narrow fit
    try:
         parm, pcov = curve_fit(gaussian, wave_x, wave_counts, p0=(central,1.0,0),
                                bounds=((central-fit_range, 0, -np.inf), (central+fit_range, np.inf, np.inf)))
         fit_wave = gaussian(xfit, parm[0], parm[1], parm[2])
         rms_wave = gaussian(wave_x, parm[0], parm[1], parm[2])
         error = rms(wave_counts, rms_wave)

    except:
        log.error("Could not fit gaussian.")
        return 0.0

    title = ""

    if snr is None:
        snr = est_snr(wavelengths,values,central)

    score = snr
    sk = -999
    ku = -999
    si = -999
    dx0 = -999
    rh = -999
    mx_norm = max(wave_counts)/100.0

    #fit around designated emis line
    if (fit_wave is not None):
        sk = skew(fit_wave)
        ku = kurtosis(fit_wave) # remember, 0 is tail width for Normal Dist. ( ku < 0 == thinner tails)
        si = parm[1] #*1.9 #scale to angstroms
        dx0 = (parm[0]-central) #*1.9

        #si and ku are correlated at this scale, for emission lines ... fat si <==> small ku

        height_pix = max(wave_counts)
        height_fit = max(fit_wave)

        if height_pix > 0:
            rh = height_fit/height_pix
        else:
            log.info("Minimum peak height (%f) too small. Score zeroed." % (height_pix))
            dqs_raw = 0.0
            score = 0.0
            rh = 0.0

        #todo: for lower S/N, sigma (width) can be less and still get bonus if fibers have larger separation

        #new_score:
        if (0.75 < rh < 1.25) and (error < 0.2): # 1 bad pixel in each fiber is okay, but no more

            #central peak position
            if abs(dx0) > 1.9:  #+/- one pixel (in AA)  from center
                val = (abs(dx0) - 1.9)** 2
                score -= val
                log.debug("Penalty for excessive error in X0: %f" % (val))


            #sigma scoring
            if si < 2.0: # and ku < 2.0: #narrow and not huge tails
                val = mx_norm*np.sqrt(2.0 - si)
                score -= val
                log.debug("Penalty for low sigma: %f" % (val))
                #note: si always > 0.0 and rarely < 1.0
            elif si < 2.5:
                pass #zero zone
            elif si < 10.0:
                val = np.sqrt(si-2.5)
                score += val
                log.debug("Bonus for large sigma: %f" % (val))
            elif si < 15.0:
                pass #unexpected, but lets not penalize just yet
            else: #very wrong
                val = np.sqrt(si-15.0)
                score -= val
                log.debug("Penalty for excessive sigma: %f" % (val))


            #only check the skew for smaller sigma
            #skew scoring
            if si < 2.5:
                if sk < -0.5: #skew wrong directionn
                    val = min(1.0,mx_norm*min(0.5,abs(sk)-0.5))
                    score -= val
                    log.debug("Penalty for low sigma and negative skew: %f" % (val))
                if (sk > 2.0): #skewed a bit red, a bit peaky, with outlier influence
                    val = min(0.5,sk-2.0)
                    score += val
                    log.debug("Bonus for low sigma and positive skew: %f" % (val))

            base_msg = "Fit dX0 = %g(AA), RH = %0.2f, rms = %0.2f, Sigma = %g(AA), Skew = %g , Kurtosis = %g "\
                   % (dx0, rh, error, si, sk, ku)
            log.info(base_msg)
        elif rh > 0.0:
            #todo: based on rh and error give a penalty?? maybe scaled by maximum pixel value? (++val = ++penalty)

            if (error > 0.3) and (0.75 < rh < 1.25): #really bad rms, but we did capture the peak
                val = mx_norm*(error - 0.3)
                score -= val
                log.debug("Penalty for excessively bad rms: %f" % (val))
            elif rh < 0.6: #way under shooting peak (should be a wide sigma) (peak with shoulders?)
                val = mx_norm * (0.6 - rh)
                score -= val
                log.debug("Penalty for excessive undershoot peak: %f" % (val))
            elif rh > 1.4: #way over shooting peak (super peaky ... prob. hot pixel?)
                val = mx_norm * (rh - 1.4)
                score -= val
                log.debug("Penalty for excessively overshoot peak: %f" % (val))
        else:
            log.info("Too many bad pixels or failure to fit peak or overall bad fit. ")
            score = 0.0
    else:
        log.info("Unable to fit gaussian. ")
        score = 0.0

    if show_plot:
        if error is None:
            error = -1
        title += "Score = %0.2f (%0.1f), SNR = %0.2f (%0.1f)\n" \
                 "dX0 = %0.2f, RH = %0.2f, RMS = %f\n"\
                 "Sigma = %0.2f, Skew = %0.2f, Kurtosis = %0.2f"\
                  % (score, signal_calc_scaled_score(score),snr,signal_calc_scaled_score(snr),
                     dx0, rh, error, si, sk, ku)

        fig = plt.figure()
        gauss_plot = plt.axes()

        gauss_plot.plot(wave_x,wave_counts,c='k')

        if fit_wave is not None:

            gauss_plot.plot(xfit, fit_wave, c='b')
            gauss_plot.grid(True)

            ymin = min(min(fit_wave),min(wave_counts))
            ymax = max(max(fit_wave),max(wave_counts))
        else:
            ymin = min(wave_counts)
            ymax = max(wave_counts)
        gauss_plot.set_ylabel("Summed Counts")
        gauss_plot.set_xlabel("Wavelength $\AA$ ")

        ymin *= 1.1
        ymax *= 1.1

        if abs(ymin) < 1.0: ymin = -1.0
        if abs(ymax) < 1.0: ymax = 1.0

        gauss_plot.set_ylim((ymin,ymax))
        gauss_plot.set_xlim( (np.floor(wave_x[0]),np.ceil(wave_x[-1])) )
        gauss_plot.set_title(title)
        png = 'gauss_' + str(central)+ ".png"

        log.info('Writing: ' + png)
        print('Writing: ' + png)
        fig.tight_layout()
        fig.savefig(png)
        fig.clear()
        plt.close()
        # end plotting


    return signal_calc_scaled_score(score)


def signal_calc_scaled_score(raw):
    # 5 point scale
    # A+ = 5.0
    # A  = 4.0
    # B+ = 3.5
    # B  = 3.0
    # C+ = 2.5
    # C  = 2.0
    # D+ = 1.5
    # D  = 1.0
    # F  = 0

    a_p = 14.0
    a__ = 12.5
    a_m = 11.0
    b_p = 8.0
    b__ = 7.0
    c_p = 6.0
    c__ = 5.0
    d_p = 4.0
    d__ = 3.0
    f__ = 2.0

    if raw is None:
        return 0.0
    else:
        hold = False

    if   raw > a_p : score = 5.0  #A+
    elif raw > a__ : score = 4.5 + 0.5*(raw-a__)/(a_p-a__) #A
    elif raw > a_m : score = 4.0 + 0.5*(raw-a_m)/(a__-a_m) #A-
    elif raw > b_p : score = 3.5 + 0.5*(raw-b_p)/(a_m-b_p) #B+ AB
    elif raw > b__ : score = 3.0 + 0.5*(raw-b__)/(b_p-b__) #B
    elif raw > c_p : score = 2.5 + 0.5*(raw-c_p)/(b__-c_p) #C+ BC
    elif raw > c__ : score = 2.0 + 0.5*(raw-c__)/(c_p-c__) #C
    elif raw > d_p : score = 1.5 + 0.5*(raw-d_p)/(c__-d_p) #D+ CD
    elif raw > d__ : score = 1.0 + 0.5*(raw-d__)/(d_p-d__) #D
    elif raw > f__ : score = 0.5 + 0.5*(raw-f__)/(d__-f__) #F
    elif raw > 0.0 : score =  0.5*raw/f__
    else: score = 0.0

    score = round(score,1)

    return score


def est_fwhm(wavelengths,values,central):

    num_pix = len(wavelengths)
    idx = getnearpos(wavelengths, central)
    hm = values[idx] / 2.0

    #hm = float((pv - zero) / 2.0)
    pix_width = 0

    # for centroid (though only down to fwhm)
    sum_pos_val = wavelengths[idx] * values[idx]
    sum_pos = wavelengths[idx]
    sum_val = values[idx]

    # check left
    pix_idx = idx - 1

    try:
        while (pix_idx >= 0) and (values[pix_idx] >= hm):
            sum_pos += wavelengths[pix_idx]
            sum_pos_val += wavelengths[pix_idx] * values[pix_idx]
            sum_val += values[pix_idx]
            pix_width += 1
            pix_idx -= 1

    except:
        pass

    # check right
    pix_idx = idx + 1

    try:
        while (pix_idx < num_pix) and (values[pix_idx] >= hm):
            sum_pos += wavelengths[pix_idx]
            sum_pos_val += wavelengths[pix_idx] * values[pix_idx]
            sum_val += values[pix_idx]
            pix_width += 1
            pix_idx += 1
    except:
        pass

    return pix_width

def est_noise(wavelengths,values,central,dw,xw=4.0,peaks=None,valleys=None):
    """

    :param wavelengths: [array] position (wavelength) coordinates of spectra
    :param values: [array] values of the spectra
    :param central: central wavelength aboout which to estimate noise
    :param dw: width about the central wavelength over which to estimate noise
    :param xw: width from the central wavelength to begin the dw window
               that is, average over all peaks between (c-xw-dw) and (c-xw) AND (c+xw) and (c+xw+dw)
               like a 1d annulus
    :param px: optional peak coordinates (wavelengths)
    :param pv: optional peak values (counts)
    :return: noise, zero
    """

    outlier_x = 3.0
    noise = DEFAULT_NOISE
    wavelengths = np.array(wavelengths)
    values = np.array(values)

    if dw > len(wavelengths)/2.0:
        return None, None

    try:
        # peaks, vallyes are 3D arrays = [index in original array, wavelength, value]
        if peaks is None or valleys is None:
            peaks, valleys = simple_peaks(wavelengths,values)

        #get all the peak values that are in our noise sample range
        peak_v = peaks[:,2]
        peak_w = peaks[:,1]

        peak_v = peak_v[((peak_w >= (central - xw - dw)) & (peak_w <= (central - xw))) |
                   ((peak_w >= (central + xw)) & (peak_w <= (central + xw + dw)))]

        # get all the valley values that are in our noise sample range
        valley_v = valleys[:, 2]
        valley_w = valleys[:, 1]

        valley_v = valley_v[((valley_w >= (central - xw - dw)) & (valley_w <= (central - xw))) |
                        ((valley_w >= (central + xw)) & (valley_w <= (central + xw + dw)))]

        #remove outliers (under assumption that extreme outliers are signals or errors)
        peak_v = peak_v[abs(peak_v - np.mean(peak_v)) < abs(outlier_x * np.std(peak_v))]
        valley_v = valley_v[abs(valley_v-np.mean(valley_v)) < abs(outlier_x * np.std(valley_v))]


        if len(peak_v) > 2:
            peak_noise = np.sum(peak_v**2)/len(peak_v)
        else:
            noise, zero = est_noise(wavelengths,values,central,dw*2,xw,peaks=None,valleys=None)
            return noise, zero

        if len(valley_v) > 2:
            valley_noise = np.sum(valley_v**2)/len(valley_v)
        else:
            valley_noise = DEFAULT_NOISE

        noise = peak_noise



        #average (signed) difference between peaks and valleys
        #avg = (np.mean(peak_v) - np.mean(valley_v))/2.0

        #zero point is the total average
        zero = np.mean(np.append(peak_v,valley_v))

        #noise = avg + zero

        if False:
            w = values[((wavelengths >= (central - xw - dw)) & (wavelengths <= (central - xw))) |
                       ((wavelengths >= (central + xw)) & (wavelengths <= (central + xw + dw)))]

            #pull any outliers (i.e. possible other signals)
            sd = np.std(w)
            w = w[abs(w-np.mean(w)) < abs(outlier_x*sd)]
            if len(w) > 7:
                noise = np.mean(w)


    except:
        log.error("Exception estimating noise: ", exc_info=True)

    return noise, zero


#todo: detect and estimate contiuum (? as SNR or mean value? over some range(s) of wavelength?)
# ie. might have contiuum over just part of the spectra
def est_continuum(wavengths,values,central):
    pass

def est_signal(wavelengths,values,central,xw=None):
    if xw is None:
        xw = est_fwhm(wavelengths,values,central)

    #temporary
    return values[getnearpos(wavelengths,central)]**2


def est_snr(wavelengths,values,central,dw=40.0,peaks=None,valleys=None):
    """

    :param wavelengths:
    :param values:
    :param central:
    :param dw:
    :param xw:
    :param px:
    :param pv:
    :return:
    """
    snr = None
    xw = est_fwhm(wavelengths,values,central)
    noise,zero = est_noise(wavelengths,values,central,dw,xw,peaks,valleys)

    # signal = nearest values (pv) to central ?? or average of a few near the central wavelength
    signal = est_signal(wavelengths,values,central,xw)

    snr = (signal-noise)/(noise)

    return snr


def simple_peaks(x,v,h=MIN_HEIGHT,delta_v=2.0):
    """

    :param x:
    :param v:
    :return:  #3 arrays: index of peaks, coordinate (wavelength) of peaks, values of peaks
              2 3D arrays: index, wavelength, value for (1) peaks and (2) valleys
    """

    maxtab = []
    mintab = []

    if x is None:
        x = np.arange(len(v))

    v = np.asarray(v)
    num_pix = len(v)

    if num_pix != len(x):
        log.warning('peakdet: Input vectors v and x must have same length')
        return None,None

    minv, maxv = np.Inf, -np.Inf
    minpos, maxpos = np.NaN, np.NaN

    lookformax = True

    for i in np.arange(len(v)):
        thisv = v[i]
        if thisv > maxv:
            maxv = thisv
            maxpos = x[i]
            maxidx = i
        if thisv < minv:
            minv = thisv
            minpos = x[i]
            minidx = i
        if lookformax:
            if (thisv >= h) and (thisv < maxv - delta_v):
                #i-1 since we are now on the right side of the peak and want the index associated with max
                maxtab.append((maxidx,maxpos, maxv))
                minv = thisv
                minpos = x[i]
                lookformax = False
        else:
            if thisv > minv + delta_v:
                mintab.append((minidx,minpos, minv))
                maxv = thisv
                maxpos = x[i]
                lookformax = True

    #return np.array(maxtab)[:, 0], np.array(maxtab)[:, 1], np.array(maxtab)[:, 2]
    return np.array(maxtab), np.array(mintab)


def peakdet(x,v,dw=MIN_FWHM,h=MIN_HEIGHT,dh=MIN_DELTA_HEIGHT,zero=0.0):

    #peakind = signal.find_peaks_cwt(v, [2,3,4,5],min_snr=4.0) #indexes of peaks

    #emis = zip(peakind,x[peakind],v[peakind])
    #emistab.append((pi, px, pv, pix_width, centroid))
    #return emis



    #dh (formerly, delta)
    #dw (minimum width (as a fwhm) for a peak, else is noise and is ignored) IN PIXELS
    # todo: think about jagged peaks (e.g. a wide peak with many subpeaks)
    #zero is the count level zero (nominally zero, but with noise might raise or lower)
    """
    Converted from MATLAB script at http://billauer.co.il/peakdet.html

    Returns two arrays

    function [maxtab, mintab]=peakdet(v, delta, x)
    %PEAKDET Detect peaks in a vector
    %        [MAXTAB, MINTAB] = PEAKDET(V, DELTA) finds the local
    %        maxima and minima ("peaks") in the vector V.
    %        MAXTAB and MINTAB consists of two columns. Column 1
    %        contains indices in V, and column 2 the found values.
    %
    %        With [MAXTAB, MINTAB] = PEAKDET(V, DELTA, X) the indices
    %        in MAXTAB and MINTAB are replaced with the corresponding
    %        X-values.
    %
    %        A point is considered a maximum peak if it has the maximal
    %        value, and was preceded (to the left) by a value lower by
    %        DELTA.

    % Eli Billauer, 3.4.05 (Explicitly not copyrighted).
    % This function is released to the public domain; Any use is allowed.

    """
    maxtab = []
    mintab = []
    emistab = []
    delta = dh

    if x is None:
        x = np.arange(len(v))

    v = np.asarray(v)
    num_pix = len(v)

    if num_pix != len(x):
        log.warning('peakdet: Input vectors v and x must have same length')
        return None,None

    if not np.isscalar(dh):
        log.warning('peakdet: Input argument delta must be a scalar')
        return None, None

    if dh <= 0:
        log.warning('peakdet: Input argument delta must be positive')
        return None, None

    minv, maxv = np.Inf, -np.Inf
    minpos, maxpos = np.NaN, np.NaN

    lookformax = True

    for i in np.arange(len(v)):
        thisv = v[i]
        if thisv > maxv:
            maxv = thisv
            maxpos = x[i]
            maxidx = i
        if thisv < minv:
            minv = thisv
            minpos = x[i]
            minidx = i
        if lookformax:
            if (thisv >= h) and (thisv < maxv - delta):
                #i-1 since we are now on the right side of the peak and want the index associated with max
                maxtab.append((maxidx,maxpos, maxv))
                minv = thisv
                minpos = x[i]
                lookformax = False
        else:
            if thisv > minv + delta:
                mintab.append((minidx,minpos, minv))
                maxv = thisv
                maxpos = x[i]
                lookformax = True


    #make an array, slice out the 3rd column
    #gm = gmean(np.array(maxtab)[:,2])
    peaks = np.array(maxtab)[:, 2]
    gm = np.mean(peaks)
    std = np.std(peaks)

    #now, throw out anything waaaaay above the mean (toss out the outliers and recompute mean)
    sub = peaks[np.where(peaks < (5.0*std))[0]]
    gm = np.mean(sub)

    for pi,px,pv in maxtab:
        #check fwhm (assume 0 is the continuum level)

        #minium height above the mean of the peaks (w/o outliers)
        if (pv < 1.333 * gm):
            continue

        hm = float((pv - zero) / 2.0)
        pix_width = 0

        #for centroid (though only down to fwhm)
        sum_pos_val = x[pi] * v[pi]
        sum_pos = x[pi]
        sum_val = v[pi]

        #check left
        pix_idx = pi -1

        try:
            while (pix_idx >=0) and (v[pix_idx] >= hm):
                sum_pos += x[pix_idx]
                sum_pos_val += x[pix_idx] * v[pix_idx]
                sum_val += v[pix_idx]
                pix_width += 1
                pix_idx -= 1

        except:
            pass

        #check right
        pix_idx = pi + 1

        try:
            while (pix_idx < num_pix) and (v[pix_idx] >= hm):
                sum_pos += x[pix_idx]
                sum_pos_val += x[pix_idx] * v[pix_idx]
                sum_val += v[pix_idx]
                pix_width += 1
                pix_idx += 1
        except:
            pass

        #check local region around centroid
        centroid_pos = sum_pos_val / sum_val #centroid is an index

        #what is the average value in the vacinity of the peak (exlcuding the area under the peak)
        side_pix = max(20,pix_width)
        left = max(0,(pi - pix_width)-side_pix)
        sub_left = v[left:(pi - pix_width)]
        gm_left = np.mean(v[left:(pi - pix_width)])

        right = min(num_pix,pi+pix_width+side_pix+1)
        sub_right = v[(pi + pix_width):right]
        gm_right = np.mean(v[(pi + pix_width):right])

        #minimum height above the local gm_average
        #note: can be a problem for adjacent peaks?
        if pv < (2.0 * np.mean(np.concatenate((sub_left,sub_right)))):
            continue

        #check vs minimum width
        if not (pix_width < dw):
            #see if too close to prior peak (these are in increasing wavelength order)
            if len(emistab) > 0:
                if (px - emistab[-1][1]) > 6.0:
                    emistab.append((pi, px, pv,pix_width,centroid_pos))
                else: #too close ... keep the higher peak
                    if pv > emistab[-1][2]:
                        emistab.pop()
                        emistab.append((pi, px, pv, pix_width, centroid_pos))
            else:
                emistab.append((pi, px, pv, pix_width, centroid_pos))


    #return np.array(maxtab), np.array(mintab)
    return emistab


class EmissionLine():
    def __init__(self,name,w_rest,plot_color,solution=True,z=0,score=0.0):
        self.name = name
        self.w_rest = w_rest
        self.w_obs = w_rest * (1.0 + z)
        self.z = z
        self.color = plot_color
        self.solution = solution #True = can consider this as the target line
        self.score = score

    def redshift(self,z):
        self.z = z
        self.w_obs = self.w_rest * (1.0 + z)
        return self.w_obs




class Classifier_Solution:
    def __init__(self):
        self.score = 0.0
        self.frac_score = 0.0
        self.z = 0.0
        self.central_rest = 0.0

        self.emission_line = None

        self.lines = [] #list of EmissionLine


class Spectrum:
    """
    helper functions for spectra
    actual spectra data is kept in fiber.py
    """

    def __init__(self):

        self.emission_lines = [EmissionLine("Ly$\\alpha$ ", 1216, 'red'),
                               EmissionLine("OII ", 3727, 'green'),
                               EmissionLine("OIII", 4959, "lime"), EmissionLine("OIII", 5007, "lime"),
                               EmissionLine("CIII", 1909, "purple"),
                               EmissionLine("CIV ", 1549, "black"),
                               EmissionLine("H$\\beta$ ", 4861, "blue"),
                               EmissionLine("HeII", 1640, "orange"),
                               EmissionLine("MgII", 2798, "magenta", solution=False),
                               EmissionLine("H$\\gamma$ ", 4341, "royalblue", solution=False),
                               EmissionLine("NV ", 1240, "teal", solution=False),
                               EmissionLine("SiII", 1260, "gray", solution=False)]

        self.wavelengths = []
        self.values = [] #could be fluxes or counts or something else
        self.central = None

        self.solutions = []

    def set_spectra(self,wavelengths, values, central):
        del self.wavelengths[:]
        del self.values[:]

        self.wavelengths = wavelengths
        self.values = values
        self.central = central


    def classify(self,wavelengths = None,values = None,central = None):
        #for now, just with additional lines
        #todo: later add in continuum
        #todo: later add in bayseian stuff
        if (wavelengths is not None) and (values is not None) and (central is not None):
            self.set_spectra(wavelengths,values,central)
        solutions = self.classify_with_additional_lines(wavelengths,values,central)

        del self.solutions[:]
        self.solutions = solutions

        return solutions

    def classify_with_additional_lines(self,wavelengths = None,values = None,central = None):
        """
        using the main line
        for each possible classification of the main line
            for each possible additional line
                if in the range of the spectrum
                    fit a line (?gaussian ... like the score?) to the exact spot of the additional line
                        (allow the position to shift a little)
                    get the score and S/N (? how best to get S/N? ... look only nearby?)
                    if score is okay and S/N is at least some minium (say, 2)
                        add to weighted solution (say, score*S/N)
                    (if score or S/N not okay, skip and move to the next one ... no penalties)

        best weighted solution wins
        ?what about close solutions? maybe something where we return the best weight / (sum of all weights)?
        or (best weight - 2nd best) / best ?

        what to return?
            with a clear winner:
                redshift of primary line (z)
                rest wavelength of primary line (e.g. effectively, the line identification) [though with z is redundant]
                list of additional lines found (rest wavelengths?)
                    and their scores or strengths?

        should return all scores? all possible solutions? maybe a class called classification_solution?

        """

        if (values is None) or (wavelengths is None) or (central is None):
            values = self.values
            wavelengths = self.wavelengths
            central = self.central

        solutions = []
        total_score = 0.0 #sum of all scores (use to represent each solution as fraction of total score)


        #todo:
        #for each self.emission_line
        #   run down the list of remianing self.emission_lines and calculate score for each
        #   make a copy of each emission_line, set the score, save to the self.lines list []
        #
        #sort solutions by score

        max_w = max(wavelengths)
        min_w = min(wavelengths)

        for e in self.emission_lines:

            sol = Classifier_Solution()
            sol.z = central/e.w_rest - 1.0
            sol.central_rest = e.w_rest
            sol.emission_line = copy.deepcopy(e)
            sol.emission_line.w_obs = sol.emission_line.w_rest*(1.0 + sol.z)
            sol.emission_line.solution = True

            for a in self.emission_lines:
                if e == a:
                    continue

                a_central = a.w_rest*(sol.z+1.0)
                if (a_central > max_w) or (a_central < min_w):
                    continue

                scr = signal_score(wavelengths, values,a_central )

                if scr > 0.0:
                    total_score += scr
                    sol.score += scr
                    l = copy.deepcopy(a)
                    l.w_obs = l.w_rest * (1.0 + sol.z)
                    l.score = scr
                    sol.lines.append(l)

            if sol.score > 0.0:
                solutions.append(sol)

        for s in solutions:
            s.frac_score = s.score/total_score

        #sort by score
        solutions.sort(key=lambda x: x.score, reverse=True)

        #todo: remove ... temporary
        for s in solutions:
            print(s.frac_score, s.score, s.emission_line.name, s.z, s.central_rest*(1.0+s.z),s.central_rest)



        return solutions



    def build_full_width_spectrum(self, counts = None, wavelengths = None, central_wavelength = None,
                                  show_skylines=True, show_peaks = True, name=None,
                                  dw=MIN_FWHM,h=MIN_HEIGHT,dh=MIN_DELTA_HEIGHT,zero=0.0):


        use_internal = False
        if (counts is None) or (wavelengths is None) or (central_wavelength is None):
            counts = self.values
            wavelengths = self.wavelengths
            central_wavelength = self.central
            use_internal = True


        # fig = plt.figure(figsize=(5, 6.25), frameon=False)
        fig = plt.figure(figsize=(8, 3), frameon=False)
        plt.subplots_adjust(left=0.05, right=0.95, top=1.0, bottom=0.0)

        dy = 1.0 / 5.0  # + 1 skip for legend, + 2 for double height spectra + 2 for double height labels

        # this is the 1D averaged spectrum
        #textplot = plt.axes([0.025, .6, 0.95, dy * 2])
        specplot = plt.axes([0.05, 0.20, 0.90, 0.40])
        #specplot = plt.axes([0.025, 0.20, 0.95, 0.40])

        # they should all be the same length
        # yes, want round and int ... so we get nearest pixel inside the range)
        left = wavelengths[0]
        right = wavelengths[-1]

        try:
            mn = np.min(counts)
            mn = max(mn, -20)  # negative flux makes no sense (excepting for some noise error)
            mx = np.max(counts)
            ran = mx - mn
            specplot.step(wavelengths, counts,  where='mid', lw=1)

            specplot.axis([left, right, mn - ran / 20, mx + ran / 20])
            yl, yh = specplot.get_ylim()

            specplot.locator_params(axis='y', tight=True, nbins=4)


            if show_peaks:
                #emistab.append((pi, px, pv,pix_width,centroid))
                peaks = peakdet(wavelengths, counts,dw,h,dh,zero)

                scores = []
                for p in peaks:
                    scores.append(signal_score(wavelengths, counts, p[1]))

                #for i in range(len(scores)):
                #    print(peaks[i][0],peaks[i][1], peaks[i][2], peaks[i][3], peaks[i][4], scores[i])

                if (peaks is not None) and (len(peaks) > 0):
                    specplot.scatter(np.array(peaks)[:, 1], np.array(peaks)[:, 2], facecolors='none', edgecolors='r')

                    for i in range(len(peaks)):
                        h = peaks[i][2]
                        specplot.annotate(str(scores[i]),xy=(peaks[i][1],h),xytext=(peaks[i][1],h),fontsize=6)



            #textplot = plt.axes([0.025, .6, 0.95, dy * 2])
            textplot = plt.axes([0.05, .6, 0.90, dy * 2])
            textplot.set_xticks([])
            textplot.set_yticks([])
            textplot.axis(specplot.axis())
            textplot.axis('off')

            if central_wavelength > 0:
                wavemin = specplot.axis()[0]
                wavemax = specplot.axis()[1]
                legend = []
                name_waves = []
                obs_waves = []

                rec = plt.Rectangle((central_wavelength - 20.0, yl), 2 * 20.0, yh - yl, fill=True, lw=1, color='y', zorder=1)
                specplot.add_patch(rec)

                if use_internal and (len(self.solutions) > 0):

                    e = self.solutions[0].emission_line

                    z = self.solutions[0].z

                    #plot the central (main) line
                    y_pos = textplot.axis()[2]
                    textplot.text(e.w_obs, y_pos, e.name + " {", rotation=-90, ha='center', va='bottom',
                                  fontsize=12, color=e.color)  # use the e color for this family

                    #plot the additional lines
                    for f in self.solutions[0].lines:
                        y_pos = textplot.axis()[2]
                        textplot.text(f.w_obs, y_pos, f.name + " {", rotation=-90, ha='center', va='bottom',
                                      fontsize=12, color=e.color)  # use the e color for this family


                    #todo: show the fractional score?
                    #todo: show the next highest possibility?
                    legend.append(mpatches.Patch(color=e.color,
                                                 label="%s %0.1f (%0.2f)" %(e.name,self.solutions[0].score,
                                                                            self.solutions[0].frac_score)))
                    name_waves.append(e.name)


                else:
                    for e in self.emission_lines:
                        if not e.solution:
                            continue

                        z = central_wavelength / e.w_rest - 1.0

                        if (z < 0):
                            continue

                        count = 0
                        for f in self.emission_lines:
                            if (f == e) or not (wavemin <= f.redshift(z) <= wavemax):
                                continue

                            count += 1
                            y_pos = textplot.axis()[2]
                            for w in obs_waves:
                                if abs(f.w_obs - w) < 20:  # too close, shift one vertically
                                    y_pos = (textplot.axis()[3] - textplot.axis()[2]) / 2.0 + textplot.axis()[2]
                                    break

                            obs_waves.append(f.w_obs)
                            textplot.text(f.w_obs, y_pos, f.name + " {", rotation=-90, ha='center', va='bottom',
                                          fontsize=12, color=e.color)  # use the e color for this family

                        if (count > 0) and not (e.name in name_waves):
                            legend.append(mpatches.Patch(color=e.color, label=e.name))
                            name_waves.append(e.name)

            # make a legend ... this won't work as is ... need multiple colors
            skipplot = plt.axes([.025,0.0, 0.95, dy])
            skipplot.set_xticks([])
            skipplot.set_yticks([])
            skipplot.axis(specplot.axis())
            skipplot.axis('off')
            skipplot.legend(handles=legend, loc='center', ncol=len(legend), frameon=False,
                            fontsize='small', borderaxespad=0)

        except:
            log.warning("Unable to build full width spec plot.", exc_info=True)

        if show_skylines:
            try:
                yl, yh = specplot.get_ylim()

                central_w = 3545
                half_width = 10
                rec = plt.Rectangle((central_w - half_width, yl), 2 * half_width, yh - yl, fill=True, lw=1,
                                    color='gray', alpha=0.5, zorder=1)
                specplot.add_patch(rec)

                central_w = 5462
                half_width = 5
                rec = plt.Rectangle((central_w - half_width, yl), 2 * half_width, yh - yl, fill=True, lw=1,
                                    color='gray', alpha=0.5, zorder=1)
                specplot.add_patch(rec)
            except:
                log.warning("Unable add skylines.", exc_info=True)

        if name is not None:
            try:
                plt.savefig(name+".png", format='png', dpi=300)
            except:
                log.warning("Unable save plot to file.", exc_info=True)


        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300)

        plt.close(fig)
        return buf


