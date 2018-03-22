#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position, redefined-outer-name, range-builtin-not-iterating

"""
Scan the log-likelihood space.
"""

from __future__ import absolute_import, division, print_function

__all__ = ['scan_llh', 'parse_args']

__author__ = 'J.L. Lanfranchi'
__license__ = '''Copyright 2017 Justin L. Lanfranchi

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
from collections import OrderedDict
from os.path import abspath, dirname, join
import pickle
import sys
import time

import numpy as np

from pisa.utils.format import hrlist2list

if __name__ == '__main__' and __package__ is None:
    RETRO_DIR = dirname(dirname(abspath(__file__)))
    if RETRO_DIR not in sys.path:
        sys.path.append(RETRO_DIR)
from retro import HYPO_PARAMS_T, instantiate_objects
from retro.likelihood import get_llh
from retro.scan import scan
from retro.utils.misc import expand, mkdir


def parse_args(description=__doc__):
    """Parse command-line arguments"""
    parser = ArgumentParser(description=description)

    parser.add_argument(
        '--outdir', required=True
    )

    for dim in HYPO_PARAMS_T._fields:
        parser.add_argument(
            '--{}'.format(dim.replace('_', '-')), nargs='+', required=True,
            help='''Hypothses will take this(these) value(s) for dimension
            {dim_hr}. Specify a single value to not scan over this dimension;
            specify a human-readable string of values, e.g. '0, 0.5, 1-10:0.2'
            scans 0, 0.5, and from 1 to 10 (inclusive of both endpoints) with
            stepsize of 0.2.'''.format(dim_hr=dim.replace('_', ' '))
        )

    dom_tables_kw, hypo_kw, hits_kw, scan_kw = (
        instantiate_objects.parse_args(parser=parser)
    )

    #print('')
    #print('dom_tables_kw:', dom_tables_kw)
    #print('')
    #print('hypo_kw:', hypo_kw)
    #print('')
    #print('hits_kw:', hits_kw)
    #print('')
    #print('scan_kw:', scan_kw)
    #print('')

    return dom_tables_kw, hypo_kw, hits_kw, scan_kw


def sort_dict(d):
    """Return an OrderedDict like `d` but with sorted keys."""
    return OrderedDict([(k, d[k]) for k in sorted(d.keys())])


def scan_llh(dom_tables_kw, hypo_kw, hits_kw, scan_kw):
    """Script "main" function"""
    t00 = time.time()

    scan_values = []
    for dim in HYPO_PARAMS_T._fields:
        val_str = ''.join(scan_kw.pop(dim))
        val_str.replace('pi', format(np.pi, '.17e'))
        scan_values.append(hrlist2list(val_str))

    dom_tables = instantiate_objects.setup_dom_tables(**dom_tables_kw)
    hypo_handler = instantiate_objects.setup_discrete_hypo(**hypo_kw)
    hits_generator = instantiate_objects.get_hits(**hits_kw)

    # Pop 'outdir' from `scan_kw` since we don't want to store this info in
    # the metadata dict.
    outdir = expand(scan_kw.pop('outdir'))
    mkdir(outdir)

    print('Scanning paramters')
    t0 = time.time()

    metric_kw = dict(
        sd_indices=dom_tables.loaded_sd_indices,
        time_window=None,
        hypo_handler=hypo_handler,
        dom_tables=dom_tables,
        tdi_table=None
    )

    n_points_total = 0
    metric_vals = []
    for _, hits, time_window in hits_generator:
        metric_kw['hits'] = hits
        metric_kw['time_window'] = time_window

        t1 = time.time()
        metric_vals.append(
            scan(scan_values=scan_values, metric=get_llh, metric_kw=metric_kw)
        )
        dt = time.time() - t1

        n_points = metric_vals[-1].size
        n_points_total += n_points
        print('  ---> {:.3f} s, {:d} points ({:.3f} ms per LLH)'
              .format(dt, n_points, dt/n_points*1e3))
    dt = time.time() - t0

    info = OrderedDict([
        ('hypo_params', HYPO_PARAMS_T._fields),
        ('scan_values', scan_values),
        ('metric_name', 'llh'),
        ('metric_vals', metric_vals),
        ('scan_kw', sort_dict(scan_kw)),
        ('dom_tables_kw', sort_dict(dom_tables_kw)),
        ('hypo_kw', sort_dict(hypo_kw)),
        ('hits_kw', sort_dict(hits_kw)),
    ])

    outfpath = join(outdir, 'scan.pkl')
    print('Saving results in pickle file, path "{}"'.format(outfpath))
    pickle.dump(info, open(outfpath, 'wb'), protocol=pickle.HIGHEST_PROTOCOL)

    print('Total time to scan: {:.3f} s; {:.3f} ms avg per LLH'
          .format(time.time() - t00, dt/n_points_total*1e3))

    return metric_vals, info


if __name__ == '__main__':
    metric_vals, info = scan_llh(*parse_args()) # pylint: disable=invalid-name
