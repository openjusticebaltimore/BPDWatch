import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from OpenOversight.app.models import db  # noqa E402

suffixes = [
    'Sr',
    'Jr',
    'II',
    '2nd',
    'III',
    '3rd',
    'IV',
    '4th'
]

name_re = re.compile(r"^(?P<last_name>[a-zA-Z- '\.]+?)(?: (?P<suffix>(?:" + r"|".join(suffixes) + r"))\.?)?,(?P<first_name>[a-zA-Z- '\.]+?)(?: (?P<middle_initial>[a-zA-Z])\.?)?$")
last_name_re = re.compile(r"^(?P<last_name>[a-zA-Z- '\.]+?)(?: (?P<suffix>(?:" + r"|".join(suffixes) + r"))\.?)?$")
other_id_re = re.compile(r"^(?P<first_name>[a-zA-Z']+) (?P<last_name>[a-zA-Z- '\.]+): Custom Identifier/Police Sequence Number/(?P<seq_no>[A-Za-z][\dA-Za-z]\d\d)$")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)