from numpy.core.numeric import full
import pandas as pd
import os
import sys
import csv
import re
from datetime import datetime
from utils import eprint, other_id_re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from OpenOversight.app import create_app, models  # noqa E402
from OpenOversight.app.models import Assignment, db  # noqa E402

CSV_FILENAME = 'rosters/Workday Demographics Report 11.18.21 reviewed.csv'
DEPARTMENT_ID = 1

app = create_app('development')
db.app = app

scraped_jobs = []
existing_jobs = [job.job_title for job in models.Job.query.filter_by(department_id=1).all()]
code_to_job = {}

bad_name_case = [
    ('K608', 'Daniel', 'Quezada'),
    ('K611', 'Zain', 'Harpsupshur'),
    ('K823', 'James', 'Ulysse'),
    ('H014', 'Noraima', 'DeJesus-Willem'),
    ('G542', 'Albert', 'DellaRocco'),
    ('T830', 'LaTonya', 'Dutton'),
    ('J552', 'Dylan', 'LaPorta'),
    ('J483', 'Christopher', 'LeMaitre'),
    ('J467', 'DaSean', 'Moore'),
    ('T497', 'Denise', 'ONeale'),
    ('T650', 'DeRond', 'Ricks'),
    ('G337', 'McKinley', 'Smith'),
    ('M801', 'LaWang', 'Hyman'),
    ('K270', 'Ralph', 'DiLucci'),
    ('K307', "D'Ara", 'Tatum'),
    ('D721', 'Richard', 'McCarthy'),
    ('I795', 'Larry', 'Mackall'),
    ('J500', 'Destinee', 'Macklin'),
    ('I783', 'Ellesse', 'McCray-Lathan'),
    ('J971', 'Brendan', 'Machado'),
    ('T929', 'Darcy', 'Machado')
]

name_fixes = [
    ('I759', 'K Chinyere', 'Zellars'),
    ('H322', 'Jason Loui', 'Hoover'),
    ('K569', 'Cierra Lynn', 'Thurmond'),
    ('K168', 'Zhi Fan', 'Zou'),
    ('S900', 'Ayesha A', 'Larkins'),
    ('K092', 'Antonios Zachary', 'Cornias'),
    ('K668', 'William', 'Miller'),
    ('TA80', 'To Uyen', 'Nguyen'),
    ('G321', 'Bryant', 'Fair')
]


def clean_name_capitalization(row):
    for cop in bad_name_case:
        if row['unique_internal_identifier'] == cop[0]:
            row['first_name'] = cop[1]
            row['last_name'] = cop[2]
            return row
    return row


def clean_middle_initial(row):
    row.fillna('', inplace=True)
    officer = models.Officer.query.filter_by(unique_internal_identifier=row['unique_internal_identifier']).one_or_none()
    middle_initial = row['middle_initial'].replace('.','')
    if officer and officer.middle_initial and len(officer.middle_initial) > len(middle_initial):
        row['middle_initial'] = officer.middle_initial
    else:
        row['middle_initial'] = middle_initial
    return row


def parse_name_seq_no(row):
    full_name_seq_no = row['Other IDs']
    if 'Suzanne Gray' in full_name_seq_no:
        row['first_name'] = 'Suzanne'
        row['last_name'] = 'Gray'
        row['unique_internal_identifier'] = 'M733'
        return row
    matches = other_id_re.fullmatch(full_name_seq_no)
    try:
        last_name = matches.group('last_name')
        first_name = matches.group('first_name')
        seq_no = matches.group('seq_no').upper()
        assert first_name and last_name and seq_no
    except:
        raise Exception('Unable to parse name/seq no {}'.format(full_name_seq_no))
    row['first_name'] = first_name
    row['last_name'] = last_name
    row['unique_internal_identifier'] = seq_no
    mc_match = re.fullmatch(r'^(Ma?c)([a-z])([a-z]+)$', row['last_name'])
    if mc_match:
        row['last_name'] = mc_match.group(1) + mc_match.group(2).upper() + mc_match.group(3)
    o_match = re.fullmatch(r"^O'([a-z])([a-z]+)$", row['last_name'])
    if o_match:
        row['last_name'] = "O'" + o_match.group(1).upper() + o_match.group(2)
    for name in name_fixes:
        if seq_no == name[0]:
            row['first_name'] = name[1]
            row['last_name'] = name[2]
            break
    if seq_no == 'K668':
        row['suffix'] = 'IV'
    return row


def check_job_title(row):
    job_title = row['job_title']
    job_title = job_title.replace(' EID','')  # No need to keep the EID distinction in BPD Watch
    job_title = job_title.replace(' (On Leave)','')
    job_title = job_title.replace(
        'Director of Governmental Affairs',
        'Director Of Government Affairs'
    )
    job_title = job_title.replace(
        'Police officer',
        'Police Officer'
    )
    job_title = job_title.replace(' Tech ',' Technician ')
    job_title = job_title.replace(' Supv',' Supervisor')
    job_title = job_title.replace(' Srvc',' Services')
    job_title = job_title.replace('Lead Tech','Lead Technician')
    job_title = job_title.replace(' Prog ',' Program ')
    job_title = job_title.replace(
        'Avionics Technician Power Plant Mech',
        'Avionics Technician/Airframe & Powerplant Mechanic'
    )
    job_title = job_title.replace(
        'Aviation Mech Inspector A & P',
        'Aviation Mechanic Inspector - Airframe & Powerplant'
    )
    job_title = job_title.replace(
        'BACKGROUND INVESTIGATOR',
        'Background Investigator'
    )
    if job_title not in scraped_jobs and job_title not in existing_jobs:
        eprint("WARNING: Job title not found: {}".format(job_title))
    row['job_title'] = job_title
    return row


def clean_gender(gender):
    if gender == 'Male':
        return 'M'
    elif gender == 'Female':
        return 'F'
    elif gender == 'Not Specified':
        return 'Not Sure'


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


def remove_known_assignments(row):
    officer = models.Officer.query.filter_by(unique_internal_identifier=row['unique_internal_identifier']).one_or_none()
    if officer:
        for assignment in officer.assignments:
            if assignment.job.job_title == row['job_title']:
                row['job_title'] = None
    return row


def clean_employment_date(data):
    if data.strip():
        data = datetime.strptime(data, '%m/%d/%y').strftime('%Y-%m-%d')
    return data


def main():
    eprint('Loading job codes')
    for filename in ['scraped_job_codes.csv', 'additional_job_codes.csv']:
        with open(os.path.join(os.path.dirname(__file__), filename), 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                code_to_job[int(row['Job Code'])] = row['Job Title']
                scraped_jobs.append(row['Job Title'])
    eprint("Importing raw roster", CSV_FILENAME)
    dirty = pd.read_csv(os.path.join(os.path.dirname(__file__), CSV_FILENAME), encoding='latin1')
    eprint('Removing bad rows')
    dirty = dirty[dirty['Worker'].str.contains('BPD Ofc')==False]
    clean = pd.DataFrame()
    clean['Other IDs'] = dirty['Other IDs']
    clean.dropna(subset = ["Other IDs"], inplace=True)
    clean['suffix'] = ''
    clean = clean.apply(parse_name_seq_no, axis='columns')
    eprint('Cleaning name capitalization')
    clean = clean.apply(clean_name_capitalization, axis='columns')
    eprint('Setting gender')
    clean['gender'] = dirty['Gender'].apply(clean_gender)
    # eprint('Setting race')
    # clean['race'] = dirty['Ethnic Group'].apply(int_to_race)
    eprint('Setting age')
    clean['age'] = dirty['Date of Birth Age']
    eprint('Setting rank')
    clean['job_title'] = dirty['Business Title']
    clean = clean.apply(check_job_title, axis='columns')
    clean = clean.apply(remove_known_assignments, axis='columns')
    clean['employment_date'] = dirty['Original Hire Date'].apply(clean_employment_date)
    clean.insert(0, "department_id", DEPARTMENT_ID)

    del clean['Other IDs']
    # import pdb; pdb.set_trace()
    
    clean.to_csv(sys.stdout, index=False)


if __name__ == '__main__':
    main()