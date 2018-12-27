import pandas as pd
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from OpenOversight.app import create_app, models
from OpenOversight.app.models import db

app = create_app('development')
db.app = app

columns = {
    # 'Location': 'location',
    'EMPLID': 'employee_id',
    'Last Name': 'last_name',
    'First Name': 'first_name',
    # 'Middle Name': 'middle_initial',
    'SEX': 'sex',
    'Ethnic Group': 'ethnic_group',
    'Service Date': 'service_date',
    'Rehire Date': 'rehire_date',
    'Promotion Date': 'promotion_date',
    'Job Code': 'job_code',
    'Job Title': 'job_title',
    'Supv ID': 'supervisor_employee_id',
    # 'In Lieu': 'in_lieu',
    'Position Number': 'position_number',
    'Grade': 'grade',
    'GL Pay Type': 'gl_pay_type',
    # 'Locatlity': 'locality', # sic
    'SEQ#': 'seq_no'
}

def load(filename):
    print("Importing raw roster")
    df = pd.read_excel(filename)
    for column in columns.keys():
        assert column in df.columns
    df.rename(columns=columns, inplace=True)
    try:
        df.to_sql('roster_raw', db.engine)
    except ValueError:
        print('Raw roster already imported')
    else:
        print('Raw roster successfully imported')

    departments = models.Department.query.all()
    bpd = None
    for department in departments:
        if department.name == 'Baltimore City Police Department':
            print('Department already created')
            bpd = department
    if not bpd:
        print("Creating department")
        bpd = models.Department(name='Baltimore City Police Department',
            short_name='BPD')
        db.session.add(bpd)
        db.session.commit()

    print("Deleting previous officer records")
    db.session.execute(
        models.Officer.__table__.delete().where(models.Officer.department_id == bpd.id)
    )
    db.session.commit()

    print("Importing new officer records")
    for pig in df.itertuples():
        # print(pig.seq_no)
        try:
            officer = models.Officer(
                department_id = bpd.id,
                last_name = pig.last_name,
                first_name = pig.first_name,
                race = pig.ethnic_group,
                # middle_initial = pig.middle_initial.strip() if type(pig.middle_initial) == unicode else None,
                gender = pig.sex,
                employment_date = pig.service_date,
                unique_internal_identifier = pig.seq_no
            )
        except:
            import pdb; pdb.set_trace()
        db.session.add(officer)
        db.session.commit()

        assignment = models.Assignment(
            officer_id = officer.id,
            rank = pig.job_title
        )
        db.session.add(assignment)

    db.session.commit()
    print("Finished data import!")

if __name__ == '__main__':
    load('Employee_Information_for_Release_10.31.2018.xlsx')