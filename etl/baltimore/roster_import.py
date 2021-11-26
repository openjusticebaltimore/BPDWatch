import pandas as pd
import os
import sys
import csv
import re
from datetime import datetime
from utils import eprint

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from OpenOversight.app import create_app, models  # noqa E402
from OpenOversight.app.models import db  # noqa E402

CSV_FILENAME = 'rosters/HRIS Employee Demographics 12.3.20 reviewed.csv'
DEPARTMENT_ID = 1

app = create_app('development')
db.app = app

jobs = []
code_to_job = {}
seq_no_re = re.compile(r"^[A-Z][\dA-Z]\d\d$")

duplicate_seq_nos = [
    'M857'
]

bad_name_case = [
    ('T970', 'Destiny', 'Cusick'),
    ('M842', 'Dennis', 'Knight'),
    ('T985', 'Sarina', 'Eames-Wardell'),
    ('K527', 'Dion', 'Nicholson'),
    ('K608', 'Daniel', 'Quezada'),
    ('K611', 'Zain', 'Harpsupshur')
]

bad_seq_nos = [
    # first name, last name, listed seq no, correct seq no
    ('Ricardo', 'Posada', 'K520', 'K620'),
    ('Ronnie', 'Anderson', 'T936', 'T396')
]


def clean_name_capitalization(row):
    for cop in bad_name_case:
        if row['unique_internal_identifier'] == cop[0]:
            row['first_name'] = cop[1]
            row['last_name'] = cop[2]
            break
    return row


def clean_last_names(data):
    if data == 'Bernardez Ruiz':
        return 'Bernardez-Ruiz'
    return data


def clean_middle_initial(row):
    row.fillna('', inplace=True)
    officer = models.Officer.query.filter_by(unique_internal_identifier=row['unique_internal_identifier']).one_or_none()
    middle_initial = row['middle_initial'].replace('.','')
    if officer and officer.middle_initial and len(officer.middle_initial) > len(middle_initial):
        row['middle_initial'] = officer.middle_initial
    else:
        row['middle_initial'] = middle_initial
    return row
    
def parse_name(row):
    full_name = row['full_name']
    matches = name_re.fullmatch(full_name)
    try:
        last_name = matches.group('last_name')
        suffix = matches.group('suffix')
        first_name = matches.group('first_name')
        middle_initial = matches.group('middle_initial')
        assert first_name and last_name
    except:
        raise Exception('Unable to parse name {}'.format(full_name))
    row['first_name'] = first_name
    row['last_name'] = last_name
    row['suffix'] = suffix

    officer = models.Officer.query.filter_by(unique_internal_identifier=row['unique_internal_identifier']).one_or_none()
    if officer and officer.middle_initial and len(officer.middle_initial) > len(middle_initial):
        row['middle_initial'] = officer.middle_initial
    else:
        row['middle_initial'] = middle_initial
    return row


def job_code_to_title(row):
    job_code = int(row['job_code'])
    job_title = row['job_title']
    try:
        job_title = code_to_job[job_code]
    except KeyError:
        job_title = job_title.replace(' EID','')  # No need to keep the EID distinction in BPD Watch
        if job_title not in jobs:
            raise Exception("Job title not found: {}".format(job_title))
    else:
        job_title = job_title.replace(' - EID','')
    row['job_title'] = job_title
    return row


def clean_gender(gender):
    if gender == 'N':
        gender = 'Not Sure'
    return gender


def int_to_race(rint):
    rint = int(rint)
    if rint == 1:
        race = 'WHITE'
    elif rint == 2:
        race = 'BLACK'
    elif rint == 3:
        race = 'HISPANIC'
    elif rint == 4:
        race = 'ASIAN PACIFIC ISLANDER'
    elif rint == 5:
        race = 'NATIVE AMERICAN'
    elif rint == 6:
        race = 'Other'
    # elif rint == 7:
    else:
        race = 'Not Sure'
    return race


def clean_seq_no(row):
    row['unique_internal_identifier'] = row['unique_internal_identifier'].replace('-','').upper()
    if not seq_no_re.fullmatch(row['unique_internal_identifier']):
        raise Exception("Invalid sequence number {}".format(row['unique_internal_identifier']))
    for cop in bad_seq_nos:
        if row['unique_internal_identifier'] == cop[2] and row['first_name'] == cop[0] and row['last_name'] == cop[1]:
            row['unique_internal_identifier'] = cop[3]
            break
    return row


def clean_assignment_date(row):
    assignment_date = None
    if not isinstance(row['promotion_date'], float) and row['promotion_date'].strip():
        assignment_date = datetime.strptime(row['promotion_date'], '%m/%d/%Y').date()
    elif not isinstance(row['rehire_date'], float) and row['rehire_date'].strip():
        assignment_date = datetime.strptime(row['rehire_date'], '%m/%d/%Y').date()
    
    if not isinstance(row['employment_date'], float) and row['employment_date'].strip() and not assignment_date:
        assignment_date = datetime.strptime(row['employment_date'], '%m/%d/%Y').date()
    
    row['star_date'] = assignment_date.strftime('%Y-%m-%d')
    return row


def clean_employment_date(data):
    if data.strip():
        data = datetime.strptime(data, '%m/%d/%Y').strftime('%Y-%m-%d')
    return data


def main():
    eprint('Loading job codes and titles')
    for filename in ['scraped_job_codes.csv', 'additional_job_codes.csv']:
        with open(os.path.join(os.path.dirname(__file__), filename), 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                code_to_job[int(row['Job Code'])] = row['Job Title']
                jobs.append(row['Job Title'])
    eprint("Importing raw roster", CSV_FILENAME)
    dirty = pd.read_csv(os.path.join(os.path.dirname(__file__), CSV_FILENAME), encoding='latin1')
    eprint('Removing bad rows')
    dirty = dirty[~dirty['SEQ# (A99 only)'].isin(duplicate_seq_nos)]
    dirty = dirty[dirty['SEQ# (A99 only)'].str.contains('BPD Ofc')==False]
    clean = pd.DataFrame()
    clean['first_name'] = dirty['First Name']
    clean['last_name'] = dirty['Last Name'].apply(clean_last_names)
    clean['unique_internal_identifier'] = dirty['SEQ# (A99 only)']
    eprint('Cleaning sequence numbers')
    clean = clean.apply(clean_seq_no, axis='columns')
    eprint('Cleaning name capitalization')
    clean = clean.apply(clean_name_capitalization, axis='columns')
    clean['middle_initial'] = dirty['Middle Name']
    eprint('Cleaning middle names')
    clean = clean.apply(clean_middle_initial, axis='columns')
    eprint('Setting gender')
    clean['gender'] = dirty['SEX'].apply(clean_gender)
    eprint('Setting race')
    clean['race'] = dirty['Ethnic Group'].apply(int_to_race)
    eprint('Setting age')
    clean['age'] = dirty['Date of Birth Age']
    eprint('Setting rank')
    clean['job_code'] = dirty['Job Code']
    clean['job_title'] = dirty['Job Title']
    clean = clean.apply(job_code_to_title, axis='columns')
    clean['employment_date'] = dirty['Service Date']
    clean['rehire_date'] = dirty['Rehire Date']
    clean['promotion_date'] = dirty['Promotion Date']
    eprint('Cleaning assignments')
    clean = clean.apply(clean_assignment_date, axis='columns')
    clean['employment_date'] = clean['employment_date'].apply(clean_employment_date)
    clean.insert(0, "department_id", DEPARTMENT_ID)
    
    del clean['rehire_date']
    del clean['promotion_date']
    del clean['job_code']

    # import pdb; pdb.set_trace()
    
    clean.to_csv(sys.stdout, index=False)


if __name__ == '__main__':
    main()