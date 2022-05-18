# =======================================================================================
#
# For usage: $python HydroUTestDriver.py --help
#
# This script runs unit tests on the hydraulics functions.
#
#
# =======================================================================================

import matplotlib as mpl
#mpl.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
#from matplotlib.backends.backend_pdf import PdfPages
import platform
import numpy as np
import os
import sys
import getopt
import code  # For development: code.interact(local=dict(globals(), **locals()))
import time
import imp
import ctypes
from ctypes import *
from operator import add


CDLParse = imp.load_source('CDLParse','../shared/py_src/CDLParse.py')
F90ParamParse = imp.load_source('F90ParamParse','../shared/py_src/F90ParamParse.py')
PyF90Utils = imp.load_source('PyF90Utils','../shared/py_src/PyF90Utils.py')


from CDLParse import CDLParseDims, CDLParseParam, cdl_param_type
from F90ParamParse import f90_param_type, GetSymbolUsage, GetPFTParmFileSymbols, MakeListUnique
from PyF90Utils import c8, ci, cchar, c8_arr, ci_arr

# Load the fortran objects via CTYPES

f90_unitwrap_obj = ctypes.CDLL('bld/UnitWrapMod.o',mode=ctypes.RTLD_GLOBAL)
f90_constants_obj = ctypes.CDLL('bld/FatesConstantsMod.o',mode=ctypes.RTLD_GLOBAL)
f90_wftfuncs_obj = ctypes.CDLL('bld/FatesHydroWTFMod.o',mode=ctypes.RTLD_GLOBAL)
f90_hydrounitwrap_obj = ctypes.CDLL('bld/HydroUnitWrapMod.o',mode=ctypes.RTLD_GLOBAL)

# Alias the F90 functions, specify the return type
# -----------------------------------------------------------------------------------

initalloc_wtfs = f90_hydrounitwrap_obj.__hydrounitwrapmod_MOD_initallocwtfs
setwrf = f90_hydrounitwrap_obj.__hydrounitwrapmod_MOD_setwrf
setwkf = f90_hydrounitwrap_obj.__hydrounitwrapmod_MOD_setwkf
th_from_psi = f90_hydrounitwrap_obj.__hydrounitwrapmod_MOD_wrapthfrompsi
th_from_psi.restype = c_double
psi_from_th = f90_hydrounitwrap_obj.__hydrounitwrapmod_MOD_wrappsifromth
psi_from_th.restype = c_double
dpsidth_from_th = f90_hydrounitwrap_obj.__hydrounitwrapmod_MOD_wrapdpsidth
dpsidth_from_th.restype = c_double
ftc_from_psi = f90_hydrounitwrap_obj.__hydrounitwrapmod_MOD_wrapftcfrompsi
ftc_from_psi.restype = c_double
dftcdpsi_from_psi = f90_hydrounitwrap_obj.__hydrounitwrapmod_MOD_wrapdftcdpsi
dftcdpsi_from_psi.restype = c_double


# Some constants
rwcft  = [1.0,0.958,0.958,0.958]
rwccap = [1.0,0.947,0.947,0.947]
pm_leaf = 1
pm_stem = 2
pm_troot = 3
pm_aroot = 4
pm_rhiz = 5

# These parameters are matched with the indices in FATES-HYDRO
vg_type = 1
cch_type = 2
tfs_type = 3

isoil1 = 0  # Top soil layer parameters (@BCI)
isoil2 = 1  # Bottom soil layer parameters

# Constants for rhizosphere
watsat = [0.567, 0.444]
sucsat = [159.659, 256.094]
bsw    = [6.408, 9.27]

unconstrained = True


# ========================================================================================
# ========================================================================================
#                                        Main
# ========================================================================================
# ========================================================================================


class vg_wrf:
    def __init__(self,index,alpha, psd, th_sat, th_res):
        self.alpha = alpha
        self.psd   = psd
        self.th_sat = th_sat
        self.th_res = th_res
        init_wrf_args = [self.alpha, self.psd, self.th_sat, self.th_res]
        iret = setwrf(ci(index),ci(vg_type),ci(len(init_wrf_args)),c8_arr(init_wrf_args))

class cch_wrf:
    def __init__(self,index,th_sat,psi_sat,beta):
        self.th_sat  = th_sat
        self.psi_sat = psi_sat
        self.beta    = beta
        init_wrf_args = [self.th_sat,self.psi_sat,self.beta]
        iret = setwrf(ci(index),ci(cch_type),ci(len(init_wrf_args)),c8_arr(init_wrf_args))

class vg_wkf:
    def __init__(self,index,alpha, psd, th_sat, th_res, tort):
        self.alpha  = alpha
        self.psd    = psd
        self.th_sat = th_sat
        self.th_res = th_res
        self.tort   = tort
        init_wkf_args = [self.alpha, self.psd,self.th_sat,self.th_res,self.tort]
        iret = setwkf(ci(index),ci(vg_type),ci(len(init_wkf_args)),c8_arr(init_wkf_args))

class cch_wkf:
    def __init__(self,index,th_sat,psi_sat,beta):
        self.th_sat  = th_sat
        self.psi_sat = psi_sat
        self.beta    = beta
        init_wkf_args = [self.th_sat,self.psi_sat,self.beta]
        iret = setwkf(ci(index),ci(cch_type),ci(len(init_wkf_args)),c8_arr(init_wkf_args))


class tfs_wrf:
    def __init__(self,index,th_sat,th_res,pinot,epsil,rwc_fd,cap_corr,cap_int,cap_slp,pmedia,hard_rate):
        self.th_sat = th_sat
        self.th_res = th_res
        self.pinot  = pinot
        self.epsil  = epsil
        self.rwc_fd = rwc_fd
        self.cap_corr = cap_corr
        self.cap_int  = cap_int
        self.cap_slp  = cap_slp
        self.pmedia   = pmedia
        self.hard_rate   = hard_rate
        init_wrf_args = [self.th_sat,self.th_res,self.pinot,self.epsil,self.rwc_fd,self.cap_corr,self.cap_int,self.cap_slp,self.pmedia,self.hard_rate]
        iret = setwrf(ci(index),ci(tfs_type),ci(len(init_wrf_args)),c8_arr(init_wrf_args))

class tfs_wkf:
    def __init__(self,index,p50,avuln):
        self.avuln = avuln
        self.p50   = p50
        init_wkf_args = [self.p50,self.avuln]
        iret = setwkf(ci(index),ci(tfs_type),ci(len(init_wkf_args)),c8_arr(init_wkf_args))


def main(argv):

    # First check to make sure python 2.7 is being used
    version = platform.python_version()
    verlist = version.split('.')

    if( not ((verlist[0] == '2') & (verlist[1] ==  '7') & (int(verlist[2])>=15) )  ):
        print("The PARTEH driver mus be run with python 2.7")
        print(" with tertiary version >=15.")
        print(" your version is {}".format(version))
        print(" exiting...")
        sys.exit(2)

    # Read in the arguments
    # =======================================================================================

#    parser = argparse.ArgumentParser(description='Parse command line arguments to this script.')
#    parser.add_argument('--cdl-file', dest='cdlfile', type=str, \
#                        help="Input CDL filename.  Required.", required=True)

#    args = parser.parse_args()


    # Set number of analysis points
    npts = 1000


    #    min_theta = np.full(shape=(2),dtype=np.float64,fill_value=np.nan)

#    wrf_type = [vg_type, vg_type, cch_type, cch_type]
#    wkf_type = [vg_type, tfs_type, cch_type, tfs_type]

#    th_ress = [0.01, 0.10, -9, -9]
#    th_sats = [0.55, 0.55, 0.65, 0.65]
#    alphas  = [1.0, 1.0, 1.0, 1.0]
#    psds    = [2.7, 2.7, 2.7, 2.7]
#    tort    = [0.5, 0.5, 0.5, 0.5]
#    beta    = [-9, -9, 6, 9]
#    avuln   = [2.0, 2.0, 2.5, 2.5]
#    p50     = [-1.5, -1.5, -2.25, -2.25]

    ncomp= 4

    rwc_fd  = [1.0,0.958,0.958,0.958]
    rwccap  = [1.0,0.947,0.947,0.947]
    cap_slp = []
    cap_int = []
    cap_corr= []
    hydr_psi0 = 0.0
    hydr_psicap = -0.6     
    hard_rate = [1.0] #marius
    print('hard rate',hard_rate[0])
    for pm in range(4):
        if (pm == 0):
            cap_slp.append(0.0)
            cap_int.append(0.0)
            cap_corr.append(1.0)
        else:
            cap_slp.append((hydr_psi0 - hydr_psicap )/(1.0 - rwccap[pm]))
            cap_int.append(-cap_slp[pm] + hydr_psi0)
            cap_corr.append(-cap_int[pm]/cap_slp[pm])


    # Allocate memory to our objective classes
    iret = initalloc_wtfs(ci(ncomp),ci(ncomp))
    print('Allocated')


    # Define the funcions and their parameters
#    vg_wrf(1,alpha=1.0,psd=2.7,th_sat=0.55,th_res=0.1)
#    vg_wkf(1,alpha=1.0,psd=2.7,th_sat=0.55,th_res=0.1,tort=0.5)


#    cch_wrf(3,th_sat=0.55, psi_sat=-1.56e-3, beta=6)
#    tfs_wkf(3,p50=-2.25, avuln=2.0)

    names=['Soil','ARoot','Stem','Leaf'] #ref
    names=['Soil','Absorbing root - Control','Absorbing root - Fully hardened','Stem - Control','Stem - Fully hardened','Leaf - Control','Leaf - Fully hardened'] #ref

    theta_sat = [0.55,0.65,0.65,0.75] #ref
    theta_sat = [0.70,0.75,0.65,0.65]
    theta_res = [0.15,0.16,0.21,0.11] #ref
    theta_res = [0.0,0.11,0.21,0.16] 
    pi=-0.5
    ep=10

    cch_wrf(1,th_sat=0.7, psi_sat=-1.56e-3, beta=6)
    cch_wkf(1,th_sat=0.7, psi_sat=-1.56e-3, beta=6)

    # Theta vs psi plots
    plt.rcParams.update({'font.size': 24})
    mpl.rcParams['lines.linewidth'] = 3

    color1 = (105./255.,132./255.,38./255.) #green
    color2 = (112./255.,48./255.,160./255.) #purple
    color3 = (255./255.,153./255.,51./255.) #orange
    color4 = (215./255.,81./255.,210./255.) #light purple
    color5 = (81./255.,148./255.,245./255.) #light purple
    color6 = (32./255.,22./255.,176./255.) #blue dark
    color7= (0./255.,206./255.,209./255.) #blue
    color8= (127./255.,96./255.,0./255.) #brun
    color9= (124./255.,179./255.,174./255.) #blue poster

    fig0, ax1 = plt.subplots(1,1,figsize=(20,15))

#---------------------first wave
    # Absorbing root
    tfs_wrf(2,th_sat=theta_sat[1],th_res=theta_res[1],pinot=-1.043478, \
            epsil=8,rwc_fd=rwc_fd[3],cap_corr=cap_corr[3], \
            cap_int=cap_int[3],cap_slp=cap_slp[3],pmedia=4,hard_rate=hard_rate[0]) # mar
    tfs_wkf(2,p50=-2.25, avuln=2.0)

    # Stem
    tfs_wrf(3,th_sat=theta_sat[2],th_res=theta_res[2],pinot=-1.22807, \
            epsil=10,rwc_fd=rwc_fd[2],cap_corr=cap_corr[2], \
            cap_int=cap_int[2],cap_slp=cap_slp[2],pmedia=2,hard_rate=hard_rate[0]) # mar
    tfs_wkf(3,p50=-2.25, avuln=4.0)
    
    # Leaf

    tfs_wrf(4,th_sat=theta_sat[3],th_res=theta_res[3],pinot=-1.465984, \
            epsil=12,rwc_fd=rwc_fd[0],cap_corr=cap_corr[0], \
            cap_int=cap_int[0],cap_slp=cap_slp[0],pmedia=1,hard_rate=hard_rate[0]) # mar
    tfs_wkf(4,p50=-2.25, avuln=2.0)

    theta = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)
    psi   = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)
    dpsidth = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)
    cdpsidth = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)

    for ic in range(ncomp):
        theta[ic,:] = np.linspace(theta_res[ic], 1.2*theta_sat[ic], num=npts)
        for i in range(npts):
            psi[ic,i] = psi_from_th(ci(ic+1),c8(theta[ic,i]))

    ax1.plot(theta[0,:],psi[0,:],'--',label='Soil',color=color3)
    ax1.plot(theta[1,:],psi[1,:],'--',label='Control - Absorbing root',color=color1)
    ax1.plot(theta[2,:],psi[2,:],'--',label='Control - Stem',color=color2)
    ax1.plot(theta[3,:],psi[3,:],'--',label='Control - Leaf',color=color7)

#-------------------second wave

    # Absorbing root
    tfs_wrf(2,th_sat=theta_sat[1],th_res=theta_res[1],pinot=-1.043478+pi, \
            epsil=8+ep,rwc_fd=rwc_fd[3],cap_corr=cap_corr[3], \
            cap_int=cap_int[3],cap_slp=cap_slp[3],pmedia=4,hard_rate=hard_rate[0]) # mar
    tfs_wkf(2,p50=-2.25, avuln=2.0)
    # Stem
    tfs_wrf(3,th_sat=theta_sat[2],th_res=theta_res[2],pinot=-1.22807+pi, \
            epsil=10+ep,rwc_fd=rwc_fd[2],cap_corr=cap_corr[2], \
            cap_int=cap_int[2],cap_slp=cap_slp[2],pmedia=2,hard_rate=hard_rate[0]) # mar
    tfs_wkf(3,p50=-2.25, avuln=4.0)
    
    # Leaf

    tfs_wrf(4,th_sat=theta_sat[3],th_res=theta_res[3],pinot=-1.465984+pi, \
            epsil=12+ep,rwc_fd=rwc_fd[0],cap_corr=cap_corr[0], \
            cap_int=cap_int[0],cap_slp=cap_slp[0],pmedia=1,hard_rate=hard_rate[0]) # mar
    tfs_wkf(4,p50=-2.25, avuln=2.0)

    theta = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)
    psi   = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)
    dpsidth = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)
    cdpsidth = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)

    for ic in range(ncomp):
        theta[ic,:] = np.linspace(theta_res[ic], 1.2*theta_sat[ic], num=npts)
        for i in range(npts):
            psi[ic,i] = psi_from_th(ci(ic+1),c8(theta[ic,i]))

#------------------end second wave

    ax1.plot(theta[1,:],psi[1,:],label='Fully hardened - Absorbing root',color=color1)
    ax1.plot(theta[2,:],psi[2,:],label='Fully hardened - Stem',color=color2)
    ax1.plot(theta[3,:],psi[3,:],label='Fully hardened - Leaf',color=color7)

    ax1.set_ylim((-25,1))
    ax1.set_xlim((0.1,0.8))
    ax1.set_ylabel('Water potential [MPa]')
    ax1.set_xlabel('Volumetric water content [m3/m3]')
    ax1.legend(loc='lower right')
    plt.savefig('pv_sensitivity/0_theta_psi.png',dpi=200,bbox_inches='tight')
    
    for ic in range(ncomp):
        for i in range(npts):
            dpsidth[ic,i]  = dpsidth_from_th(ci(ic+1),c8(theta[ic,i]))
        for i in range(1,npts-1):
            cdpsidth[ic,i] = (psi[ic,i+1]-psi[ic,i-1])/(theta[ic,i+1]-theta[ic,i-1])

    # Theta vs dpsi_dth (also checks deriv versus explicit)

    fig1, ax1 = plt.subplots(1,1,figsize=(9,6))
    for ic in range(ncomp):
        ax1.plot(theta[ic,],dpsidth[ic,],label='func')
        ax1.plot(theta[ic,],cdpsidth[ic,],label='check')
    #ax1.set_ylim((0,1000))

    ax1.set_ylabel('dPSI/dTh [MPa m3 m-3]')
    ax1.set_xlabel('VWC [m3/m3]')
    ax1.legend(loc='upper right')

    fig11, ax1 = plt.subplots(1,1,figsize=(9,6))
    for ic in range(ncomp):
        ax1.plot(theta[ic,],1.0/dpsidth[ic,],label='{}'.format(names[ic]))

    ax1.set_ylabel('dTh/dPSI/ [m3 m-3 MPa-1]')
    ax1.set_xlabel('VWC [m3/m3]')
    ax1.legend(loc='upper right')


    # Push parameters to WKF classes
    # -------------------------------------------------------------------------
    # Generic VGs

    ftc   = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)
    dftcdpsi = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)
    cdftcdpsi = np.full(shape=(ncomp,npts),dtype=np.float64,fill_value=np.nan)

    for ic in range(ncomp):
        for i in range(npts):
            ftc[ic,i] = ftc_from_psi(ci(ic+1),c8(psi[ic,i]))

            if( (ftc[ic,i]>0.9) and (theta[ic,i]<0.4) ):
                print('tpf: ',theta[ic,i],psi[ic,i],ftc[ic,i])

    for ic in range(ncomp):
        for i in range(npts):
            dftcdpsi[ic,i]  = dftcdpsi_from_psi(ci(ic+1),c8(psi[ic,i]))
        for i in range(1,npts-1):
            cdftcdpsi[ic,i] = (ftc[ic,i+1]-ftc[ic,i-1])/(psi[ic,i+1]-psi[ic,i-1])


    fig2, ax1 = plt.subplots(1,1,figsize=(9,6))
    for ic in range(ncomp):
        ax1.plot(psi[ic,:],ftc[ic,:],label='{}'.format(names[ic]))

    ax1.set_ylabel('FTC')
    ax1.set_xlabel('Psi [MPa]')
    ax1.set_xlim([-10,3])

    ax1.legend(loc='upper left')


    # FTC versus theta

    fig4, ax1 = plt.subplots(1,1,figsize=(9,6))
    for ic in range(ncomp):
        ax1.plot(theta[ic,:],ftc[ic,:],label='{}'.format(names[ic]))

    ax1.set_ylabel('FTC')
    ax1.set_xlabel('Theta [m3/m3]')
    ax1.legend(loc='upper left')

    # dFTC/dPSI

    fig3,ax1 = plt.subplots(1,1,figsize=(9,6))
    for ic in range(ncomp):
#        ax1.plot(psi[ic,:],abs(dftcdpsi[ic,:]-cdftcdpsi[ic,:])/abs(cdftcdpsi[ic,:]),label='{}'.format(ic))
        ax1.plot(psi[ic,:],dftcdpsi[ic,:],label='{}'.format(names[ic]))

    ax1.set_ylabel('dFTC/dPSI')
    ax1.set_xlabel('Psi [MPa]')
    ax1.set_xlim([-10,3])
    ax1.set_ylim([0,2])
#    ax1.set_ylim([0,10])
    ax1.legend(loc='upper right')
    #plt.show()




#    code.interact(local=dict(globals(), **locals()))

# Helper code to plot negative logs

def semilogneg(x):

    y = np.sign(x)*np.log(abs(x))
    return(y)

def semilog10net(x):

    y = np.sign(x)*np.log10(abs(x))
    return(y)


# =======================================================================================
# This is the actual call to main

if __name__ == "__main__":
    main(sys.argv)
