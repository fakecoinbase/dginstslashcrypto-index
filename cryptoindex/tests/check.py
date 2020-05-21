"Tests for `cryptoindex.calc` module."

import numpy as np
from datetime import datetime

from cryptoindex import calc


def test_Bday():

    # is Bday
    bday = '05-11-2020'
    assert calc.is_business_day(bday) == True

    # is not Bday
    not_bday = '05-10-2020'
    assert calc.is_business_day(not_bday) != True


def test_date_validation():

    # verificare
    date = datetime(2020, 1, 1)
    assert calc.validate_date(date) == True
    # not datetime
    date2 = '05-11-2020'
    assert calc.validate_date(date2) == False


def test_previous_business_day():

    # is Bday
    bday = '05-08-2020'
    bday = datetime.strptime(bday, '%m-%d-%Y')
    assert calc.previous_business_day(bday) == bday

    # is Saturday
    sat = '05-09-2020'
    sat = datetime.strptime(sat, '%m-%d-%Y')
    assert calc.previous_business_day(sat) == bday

    # is Sunday
    sun = '05-10-2020'
    sun = datetime.strptime(sun, '%m-%d-%Y')
    assert calc.previous_business_day(sun) == bday


def test_perdelta():

    start_date = datetime.strptime('01-01-2019', '%m-%d-%Y')
    stop_date = datetime.strptime('01-01-2020', '%m-%d-%Y')
    check_range = ['01-01-2019', '04-01-2019', '07-01-2019', '10-01-2019']

    test_range = calc.perdelta(start_date, stop_date)
    # creating a list from perdelta func
    test_range = [x.strftime('%m-%d-%Y') for x in test_range]

    assert test_range == check_range


def test_start_q_fix():

    str_date = ['01-01-2019', '04-01-2019', '07-01-2019', '10-01-2019']
    ts_date = np.array([1.5463008e+09, 1.5540768e+09,
                        1.5619392e+09, 1.5698880e+09])

    # coverting string in datetime and then in epoch timestamp.
    ts_array = np.array([int(datetime.strptime(x, '%m-%d-%Y').timestamp())
                         for x in str_date])

    ts_gen = calc.start_q_fix(ts_array)

    assert np.array_equal(ts_date, ts_gen)
