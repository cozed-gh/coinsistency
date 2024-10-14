import time

def unix_time_in_seconds(date):
    time_struct = time.strptime(date, "%Y-%m-%d")
    unix_time = time.mktime(time_struct)
    return unix_time