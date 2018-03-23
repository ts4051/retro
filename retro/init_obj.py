# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position

"""
Convenience functions for intializing major objects needed for Retro likelihood
processing (includes instantiating objects and loading the data needed for
them).
"""

from __future__ import absolute_import, division, print_function

__all__ = [
    'setup_dom_tables',
    'setup_discrete_hypo',
    'get_hits',
    'parse_args'
]

__author__ = 'P. Eller, J.L. Lanfranchi'
__license__ = '''Copyright 2017 Philipp Eller and Justin L. Lanfranchi

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.'''

from argparse import ArgumentParser
from os.path import abspath, dirname, splitext
import pickle
import sys
import time

import numpy as np

if __name__ == '__main__' and __package__ is None:
    RETRO_DIR = dirname(dirname(dirname(abspath(__file__))))
    if RETRO_DIR not in sys.path:
        sys.path.append(RETRO_DIR)
from retro import const
from retro.hypo.discrete_hypo import DiscreteHypo
from retro.hypo.discrete_cascade_kernels import (
    point_cascade
)
from retro.hypo.discrete_muon_kernels import (
    const_energy_loss_muon, table_energy_loss_muon
)
from retro.i3info.angsens_model import load_angsens_model
from retro.i3info.extract_gcd import extract_gcd
from retro.utils.misc import expand
from retro.tables.retro_5d_tables import (
    NORM_VERSIONS, TABLE_KINDS, Retro5DTables
)


def setup_dom_tables(
        dom_tables_kind,
        dom_tables_fname_proto,
        gcd,
        angsens_model,
        norm_version,
        sd_indices=const.ALL_STRS_DOMS,
        step_length=1.0,
        num_phi_samples=None,
        ckv_sigma_deg=None,
        template_library=None,
        compute_t_indep_exp=True,
        use_directionality=True,
        no_noise=False,
        force_no_mmap=False,
    ):
    """Instantiate and load single-DOM tables

    """
    print('Instantiating and loading single-DOM tables')
    t0 = time.time()

    if force_no_mmap:
        mmap = False
    else:
        mmap = 'uncompr' in dom_tables_kind

    if dom_tables_kind in ['raw_templ_compr', 'ckv_templ_compr']:
        template_library = np.load(template_library)
    else:
        template_library = None

    gcd = extract_gcd(gcd)

    if no_noise:
        gcd['noise'] = np.zeros_like(gcd['noise'])

    # Instantiate single-DOM tables class
    dom_tables = Retro5DTables(
        table_kind=dom_tables_kind,
        geom=gcd['geo'],
        rde=gcd['rde'],
        noise_rate_hz=gcd['noise'],
        angsens_model=angsens_model,
        compute_t_indep_exp=compute_t_indep_exp,
        use_directionality=use_directionality,
        norm_version=norm_version,
        num_phi_samples=num_phi_samples,
        ckv_sigma_deg=ckv_sigma_deg,
        template_library=template_library,
    )

    if '{subdet' in dom_tables_fname_proto:
        doms = const.ALL_DOMS
        for subdet in ['ic', 'dc']:
            if subdet == 'ic':
                strings = const.IC_STRS
            else:
                strings = const.DC_STRS

            for dom in doms:
                fpath = dom_tables_fname_proto.format(
                    subdet=subdet, dom=dom, depth_idx=dom-1
                )
                shared_table_sd_indices = []
                for string in strings:
                    sd_idx = const.get_sd_idx(string, dom)
                    if sd_idx not in sd_indices:
                        continue
                    shared_table_sd_indices.append(sd_idx)

                if not shared_table_sd_indices:
                    continue

                dom_tables.load_table(
                    fpath=fpath,
                    sd_indices=shared_table_sd_indices,
                    step_length=step_length,
                    mmap=mmap
                )
    elif '{string' in dom_tables_fname_proto:
        raise NotImplementedError()

    print('  -> {:.3f} s\n'.format(time.time() - t0))

    return dom_tables


def setup_discrete_hypo(cascade_kernel=None, cascade_samples=None,
                        track_kernel=None, track_time_step=None):
    """Convenience function for instantiating a discrete hypothesis with
    specified kernel(s).

    Parameters
    ----------
    cascade_kernel : string or None
        One of {"point" or "one_dim_cascade"}

    cascade_samples : int or None
        Required if `cascade_kernel` is "one_dim_cascade"

    track_kernel : string or None
    track_time_step : float or None

    Returns
    -------
    hypo_handler

    """
    hypo_kernels = []
    kernel_kwargs = []
    if cascade_kernel is not None:
        if cascade_kernel == 'point':
            hypo_kernels.append(point_cascade)
            kernel_kwargs.append(dict())
        else:
            raise NotImplementedError('{} cascade not implemented yet.'
                                      .format(cascade_kernel))
            #hypo_kernels.append(one_dim_cascade)
            #kernel_kwargs.append(dict(num_samples=cascade_samples))

    if track_kernel is not None:
        if track_kernel == 'const_e_loss':
            hypo_kernels.append(const_energy_loss_muon)
        else:
            hypo_kernels.append(table_energy_loss_muon)
        kernel_kwargs.append(dict(dt=track_time_step))

    hypo_handler = DiscreteHypo(
        hypo_kernels=hypo_kernels,
        kernel_kwargs=kernel_kwargs
    )

    return hypo_handler


def get_hits(hits_file, hits_are_photons, start_idx=0, num_events=None,
             angsens_model=None):
    """Generator that loads hits and, if they are raw photons, reweights and
    reformats them into "standard" hits format.

    Parameters
    ----------
    hits_file : string
    hits_are_photons : bool
    start_idx : int, optional
    num_events : int, optional
    angsens_model : string, required if `hits_are_photons`

    Yields
    ------
    event_idx : int
    event_hits
    time_window : float

    """
    if start_idx is None:
        start_idx = 0

    if num_events is None:
        events_slice = slice(start_idx, None)
    else:
        events_slice = slice(start_idx, start_idx + num_events)

    hits_file = expand(hits_file)
    _, ext = splitext(hits_file)
    if ext == '.pkl':
        with open(hits_file, 'rb') as f:
            hits = pickle.load(f)
            offset_hits_iter = hits[events_slice]
    else:
        raise NotImplementedError()

    if hits_are_photons:
        angsens_poly, _ = load_angsens_model(angsens_model)

    for event_offset, event_hits in enumerate(offset_hits_iter):
        event_idx = event_offset - start_idx
        if hits_are_photons:
            time_window = 0.0
            event_photons = event_hits
            event_hits = [const.EMPTY_HITS]*const.NUM_DOMS_TOT
            for str_dom, pinfo in event_photons.items():
                sd_idx = const.get_sd_idx(string=str_dom[0], dom=str_dom[1])
                t = pinfo[0, :]
                coszen = pinfo[4, :]
                weight = np.float32(angsens_poly(coszen))
                event_hits[sd_idx] = np.concatenate(
                    (t[np.newaxis, :], weight[np.newaxis, :]),
                    axis=0
                )
        else:
            raise NotImplementedError()

        yield event_idx, event_hits, time_window


def parse_args(description=None, dom_tables=True, hypo=True, hits=True,
               parser=None):
    """Parse command line arguments.

    If `parser` is supplied, args are added to that; otherwise, a new parser is
    generated.

    Parameters
    ----------
    description : string, optional

    dom_tables : bool
        Whether to include args for instantiating and loading single-DOM
        tables.

    hypo : bool
        Whether to include args for instantiating a DiscreteHypo and its hypo
        kernels.

    hits : bool
        Whether to include args for loading hits (either photons or pulses).

    parser : argparse.ArgumentParser, optional
        An existing parser onto which these arguments will be added.

    Returns
    -------
    dom_tables_kw, hypo_kw, hits_kw, other_kw

    """
    if parser is None:
        parser = ArgumentParser(description=description)

    if dom_tables or hits:
        parser.add_argument(
            '--angsens-model',
            choices='nominal  h1-100cm  h2-50cm  h3-30cm'.split(),
            help='''Angular sensitivity model'''
        )

    if dom_tables:
        group = parser.add_argument_group(
            title='Single-DOM tables',
            description='''Arguments used to instantiate and load single-DOM
            Retro tables'''
        )

        group.add_argument(
            '--dom-tables-kind', required=True, choices=TABLE_KINDS,
            help='''Kind of single-DOM table to use.'''
        )
        group.add_argument(
            '--dom-tables-fname-proto', required=True,
            help='''Must have one of the brace-enclosed fields "{string}" or
            "{subdet}", and must have one of "{dom}" or "{depth_idx}". E.g.:
            "my_tables_{subdet}_{depth_idx}"'''
        )
        group.add_argument(
            '--strs-doms', required=True,
            choices=['all', 'dc', 'dc_subdust']
        )

        group.add_argument(
            '--gcd', required=True,
            help='''IceCube GCD file; can either specify an i3 file, or the
            extracted pkl file used in Retro.'''
        )
        group.add_argument(
            '--norm-version', choices=NORM_VERSIONS, required=True,
            help='''Norm version.'''
        )
        group.add_argument(
            '--num-phi-samples', type=int, default=None,
        )
        group.add_argument(
            '--ckv-sigma-deg', type=float, default=None,
        )
        group.add_argument(
            '--template-library', default=None,
        )
        group.add_argument(
            '--step-length', type=float, default=1.0,
            help='''Step length used in the CLSim table generator.'''
        )
        group.add_argument(
            '--no-noise', action='store_true',
            help='''Set noise rates to 0 in the GCD (e.g. for processing
            raw photons)'''
        )
        group.add_argument(
            '--no-t-indep', action='store_true',
            help='''Do NOT load t-indep tables (time-independent expectations
            would have to be handled by specifying a TDI table'''
        )
        group.add_argument(
            '--no-dir', action='store_true',
            help='''Do NOT use source photon directionality'''
        )
        group.add_argument(
            '--force-no-mmap', action='store_true',
            help='''Specify to NOT memory map the tables. If not specified, a
            sensible default is chosen for the type of tables being used.'''
        )

    if hypo:
        group = parser.add_argument_group(
            title='Hypo',
            description='''Arguments used to instantiate hypothesis handler
            and kernels'''
        )

        group.add_argument(
            '--cascade-kernel', choices=['point', 'one_dim'], required=True,
        )
        group.add_argument(
            '--cascade-samples', type=int, default=None,
        )
        group.add_argument(
            '--track-kernel', required=True,
            choices=['const_e_loss', 'table_e_loss'],
        )
        group.add_argument(
            '--track-time-step', type=float, required=True,
        )

    if hits:
        group = parser.add_argument_group(
            title='Hits',
            description='''Arguments for loading hits (either photon-level or
            a pulse series) from events.'''
        )

        group.add_argument(
            '--hits-file', required=True,
        )
        group.add_argument(
            '--hits-are-photons', action='store_true',
        )
        group.add_argument(
            '--start-event-idx', type=int, default=0
        )
        group.add_argument(
            '--num-events', type=int, default=None
        )

    args = parser.parse_args()
    kwargs = vars(args)

    dom_tables_kw = {}
    hypo_kw = {}
    hits_kw = {}
    other_kw = {}
    if dom_tables:
        code = setup_dom_tables.__code__
        dom_tables_kw = {k: None for k in code.co_varnames[:code.co_argcount]}
    if hypo:
        code = setup_discrete_hypo.__code__
        hypo_kw = {k: None for k in code.co_varnames[:code.co_argcount]}
    if hits:
        code = get_hits.__code__
        hits_kw = {k: None for k in code.co_varnames[:code.co_argcount]}

    if dom_tables:
        strs_doms = kwargs.pop('strs_doms').strip().lower()
        if strs_doms == 'all':
            sd_indices = const.ALL_STRS_DOMS
        elif strs_doms == 'dc':
            sd_indices = const.DC_ALL_STRS_DOMS
        elif strs_doms == 'dc_subdust':
            sd_indices = const.DC_ALL_SUBDUST_STRS_DOMS
        else:
            raise ValueError(strs_doms)
        print('nubmer of doms = {}'.format(len(sd_indices)))
        kwargs['sd_indices'] = sd_indices
        kwargs['compute_t_indep_exp'] = not kwargs.pop('no_t_indep')
        kwargs['use_directionality'] = not kwargs.pop('no_dir')

    for key, val in kwargs.items():
        taken = False
        for kw in [dom_tables_kw, hypo_kw, hits_kw]:
            if key not in kw:
                continue
            kw[key] = val
            taken = True
        if not taken:
            other_kw[key] = val

    return dom_tables_kw, hypo_kw, hits_kw, other_kw