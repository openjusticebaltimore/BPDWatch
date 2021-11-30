import pandas as pd
import os
import sys
import numpy
import pdb
from utils import last_name_re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from OpenOversight.app import app  # noqa E402
from OpenOversight.app.models import db, Officer, Salary  # noqa E402
from OpenOversight.app.utils import prompt_yes_no

db.app = app

BEGIN_YEAR = 2011
END_YEAR = 2021


class SalaryImportLog:
    updated_officers = {}

    @classmethod
    def log_change(cls, officer, msg):
        if officer.id not in cls.updated_officers:
            cls.updated_officers[officer.id] = []
        log = cls.updated_officers[officer.id]
        log.append(msg)

    @classmethod
    def print_logs(cls):
        officers = Officer.query.filter(
            Officer.id.in_(cls.updated_officers.keys())).all()
        for officer in officers:
            print('Updates to officer {}:'.format(officer))
            for msg in cls.updated_officers[officer.id]:
                print(' --->', msg)


def add_salary(officer, rows, year):
    row = rows.loc[rows.first_valid_index()]

    if type(row['annualSalary']) == str:
        annual_salary = float(row['annualSalary'].replace('$', ''))
    elif type(row['annualSalary']) == float or type(row['annualSalary']) == numpy.float64:
        annual_salary = row['annualSalary']
    else:
        raise Exception(type(row['annualSalary']))

    if type(row['grossPay']) == str:
        overtime_pay = float(row['grossPay'].replace('$', '')) - annual_salary
    elif type(row['grossPay']) == float or type(row['grossPay']) == numpy.float64:
        if numpy.isnan(row['grossPay']):
            overtime_pay = 0
        else:
            overtime_pay = row['grossPay'] - annual_salary

    salary = Salary(
        officer_id=officer.id,
        salary=annual_salary,
        overtime_pay=overtime_pay or None,
        year=year,
        is_fiscal_year=True
    )
    db.session.add(salary)
    SalaryImportLog.log_change(
        officer,
        'Added salary for FY{}: Salary {}, Overtime {}'.format(year, annual_salary, overtime_pay)
    )


def import_salaries(csv_filename):
    print("Processing salary charts")
    df = pd.read_csv(csv_filename)
    # # Only want A99 department IDs
    df = df[df.loc[:, 'agencyID'].str.startswith('A99')]
    # Skip officers with redacted names
    df = df[~df.loc[:, 'lastName'].fillna('').str.startswith('BPD ')]
    # Split last name into multiple columns
    df = df.join(df.loc[:, 'lastName'].str.extract(last_name_re))


    print("Importing salaries (this may take a while)")
    try:
        # foreach officer in DB, go matching
        for officer in Officer.query.filter_by(department_id=1).order_by(Officer.id.asc()).all():
            added_salaries = False
            print(officer)
            officer_existing_salary_years = [salary.year for salary in officer.salaries]
            # for year, df in salary_sets.items():
            for year in range(BEGIN_YEAR, END_YEAR + 1):
                # Don't check for salaries for years we already have data
                if year in officer_existing_salary_years:
                    continue
                year_df = df[df.loc[:, 'fiscalYear'].str.match('FY{}'.format(year))]
                # Match on first name, last name
                rows = year_df[year_df['firstName'].fillna('').str.lower().str.match(officer.first_name.lower())]\
                    [lambda year_df: year_df['lastName'].fillna('').str.lower().str.match(officer.last_name.lower())]
                if rows.empty:
                    continue
                elif len(rows) == 1:
                    added_salaries = True
                    add_salary(officer, rows, year)
                elif len(rows) > 1:
                    # Match on (first letter of) middle initial
                    if officer.middle_initial:
                        rows = rows[rows['middleInitial'].fillna('').str.upper().str.startswith(officer.middle_initial[:1].upper())]
                    else:
                        rows = rows[rows['middleInitial'].fillna('').str.match('NA')]
                    if len(rows) == 1:
                        added_salaries = True
                        add_salary(officer, rows, year)
                    elif len(rows) > 1:
                        # Match on (equivalent) suffix
                        if officer.suffix:
                            officer_suffix = officer.suffix\
                                .lower()\
                                .replace('jr', 'ii')\
                                .replace('2nd', 'ii')\
                                .replace('3rd', 'iii')\
                                .replace('4th', 'iv')
                        else:
                            officer_suffix = ''
                        rows = rows[rows['suffix']\
                            .fillna('')\
                            .str.lower()\
                            .str.replace('.', '')\
                            .str.replace('jr', 'ii')\
                            .str.replace('2nd', 'ii')\
                            .str.replace('3rd', 'iii')\
                            .str.replace('4th', 'iv')\
                            .str.match(officer_suffix)]
                        if len(rows) == 1:
                            added_salaries = True
                            add_salary(officer, rows, year)
                        elif len(rows) > 1:
                            # Match on hiring date
                            hire_date = officer.employment_date.strftime('%m/%d/%Y')
                            rows = rows[rows.loc[:, 'hireDate'].str.startswith(hire_date)]
                            if len(rows) == 1:
                                added_salaries = True
                                add_salary(officer, rows, year)
                            elif len(rows) > 1:
                                print('Could not match on suffix or hire date for {} {} {} {}'.format(
                                        officer.first_name, officer.middle_initial,
                                        officer.last_name, officer.suffix))
                                pdb.set_trace()
            if not added_salaries and len(officer.salaries) == 0:
                print('WARNING: Officer {},{} ({}) not found in salary charts'.format(officer.last_name, officer.first_name, officer.unique_internal_identifier))
                # pdb.set_trace()
        
        print("Proposed changes:")
        SalaryImportLog.print_logs()
        if prompt_yes_no("Do you want to commit the above changes?"):
            print("Commiting changes.")
            db.session.commit()
        else:
            print("Aborting changes.")
            db.session.rollback()
    except Exception:
        db.session.rollback()
        raise


if __name__ == '__main__':
    import_salaries(sys.argv[1])
