# -*- coding: utf-8 -*-

import os
import sys

WORK_DIR = os.path.dirname(os.path.realpath(__file__))
WORK_FNAME = os.path.join(WORK_DIR, 'test$')

def bprint (*arg):
    print('{', end='')
    print(*arg, end='')
    print('...', end=' ')
    sys.stdout.flush()

def eprint (*arg):
    print(*arg, end='')
    print('}')
    sys.stdout.flush()

error = None
def safe_run (f, msg=''):
    global error
    bprint(msg)
    res = None
    try:
       res = f()
    except Exception as e:
        if not error:
            error = e
    return res

def check_res (res, gold=True, err_msg=None):
    global error
    if res == gold:
        eprint('done.')
        sys.stdout.flush()
        error = None
    else:
        eprint('FAIL!')
        sys.stdout.flush()
        raise error if error else RuntimeError(err_msg if err_msg else '')
