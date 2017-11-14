#!/usr/bin/env python
# pylint: disable=invalid-name
"""
Tabulate the retro light flux in (theta, r, t, theta_dir, deltaphi_dir) bins.
"""


from __future__ import absolute_import, division, print_function

from optparse import OptionParser
from os import path, unlink

from icecube import icetray # pylint: disable=import-error
from icecube.icetray import I3Units # pylint: disable=import-error
from icecube.clsim.tablemaker.tabulator import ( # pylint: disable=import-error
    TabulatePhotonsFromSource, generate_seed
)
from I3Tray import I3Tray # pylint: disable=import-error


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
        '--subdet', dest='subdet', type='str', default='IC',
        help='Calculate for IceCube z-pos (IC) or DeepCore z-pos (DC)'
    )
    parser.add_option(
        '--dom', dest='dom', type='int', default=0,
        help='DOM number on string for z-pos'
    )
    parser.add_option(
        '--nevts', dest='nevts', type='int', default=1000,
        help='Number of events'
    )
    opts, args = parser.parse_args()

    outfile = (
        'tables/retro_nevts%i_%s_DOM%s.fits'
        % (opts.nevts, opts.subdet, opts.dom)
    )
    if path.exists(outfile):
        unlink(outfile)

    tray = I3Tray()

    # Average Z coordinate (depth) for each layer of DOMs (see
    # `average_z_position.py`)
    ic_z = [
        501.58615386180389, 484.56641094501202, 467.53781871306592,
        450.52576974722058, 433.49294848319812, 416.48833328638324,
        399.45294854579828, 382.44884667029748, 365.4128210605719,
        348.40564121344153, 331.37281916691705, 314.36564088479065,
        297.3325641338642, 280.31782062237079, 263.28397310697113,
        246.27871821476862, 229.24294809194711, 212.23987227219803,
        195.20448733598758, 178.20051300831329, 161.16448681171124,
        144.15717980800531, 127.12435913085938, 110.11717947935446,
        93.085897103334091, 76.078589904002655, 59.045128015371468,
        42.029999953049881, 24.996410223153923, 7.9888461460001192,
        -9.0439743934533539, -26.049487190368847, -43.080769441066643,
        -60.087948872492866, -77.120897733248199, -94.128076993502106,
        -111.15923103919395, -128.16641000600961, -145.19935891567133,
        -162.20371852776944, -179.24769259721805, -196.25589713072165,
        -213.2888457469451, -230.29628186348157, -247.32910332312952,
        -264.33628121400488, -281.36910384740582, -298.34910231370191,
        -315.40756421211438, -332.38756502591644, -349.44602457682294,
        -366.45320559770636, -383.48474355844348, -400.49948746118793,
        -417.53371801131811, -434.51192259177185, -451.56307592147436,
        -468.54307634402545, -485.64474565554889, -502.7208975767478
    ]
    dc_z = [
        188.22000122070312, 178.20999799455916, 168.2000013078962,
        158.19000026157923, 148.17000034877233, 138.16000148228235,
        128.14999934605189, 118.14000047956195, 108.12571498325893,
        98.110001700265073, -159.19999912806921, -166.21000017438615,
        -173.2199990408761, -180.22999790736608, -187.23428562709265,
        -194.23999895368303, -201.25, -208.26000322614397,
        -215.26999991280692, -222.27999877929688, -229.29000200544084,
        -236.29428536551339, -243.2999986921038, -250.30999973842077,
        -257.31999860491072, -264.33000401088168, -271.34000069754467,
        -278.3499973842076, -285.35428728376115, -292.36000279017856,
        -299.36999947684154, -306.37999616350447, -313.39000156947543,
        -320.39999825613842, -327.40999494280135, -334.4142848423549,
        -341.42000034877231, -348.43000139508928, -355.44000244140625,
        -362.44999912806918, -369.46000017438615, -376.47000122070312,
        -383.47428676060269, -390.47999790736606, -397.49000331333707,
        -404.5, -411.51000104631697, -418.52000209263394,
        -425.52857317243303, -432.53428431919644, -439.53999982561385,
        -446.55000087193082, -453.55999755859375, -460.56999860491072,
        -467.58000401088168, -474.58857509068082, -481.59286063058033,
        -488.5999973842076, -495.57714407784596, -502.65428379603793
    ]

    if opts.subdet == 'IC':
        z_pos = ic_z[opts.dom]
    elif opts.subdet == 'DC':
        z_pos = dc_z[opts.dom]
    print('z_pos:', z_pos)

    icetray.logging.set_level_for_unit('I3CLSimStepToTableConverter', 'TRACE')
    icetray.logging.set_level_for_unit('I3CLSimTabulatorModule', 'DEBUG')
    icetray.logging.set_level_for_unit(
        'I3CLSimLightSourceToStepConverterGeant4', 'TRACE'
    )
    icetray.logging.set_level_for_unit(
        'I3CLSimLightSourceToStepConverterFlasher', 'TRACE'
    )

    tray.AddSegment(
        TabulatePhotonsFromSource,
        'generator',
        Seed=generate_seed(),
        PhotonSource='retro',
        Zenith=180. * I3Units.degree,
        ZCoordinate=z_pos,
        Energy=1.,
        NEvents=opts.nevts,
        Filename=outfile,
        TabulateImpactAngle=True,
        PhotonPrescale=1,
        RecordErrors=False,
        FlasherWidth=127,
        FlasherBrightness=127,
        DisableTilt=True,
        IceModel='spice_mie',
        Axes=None,
        Sensor='none'
    )

    tray.Execute()
    tray.Finish()
