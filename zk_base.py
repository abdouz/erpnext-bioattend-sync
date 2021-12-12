import datetime
from threading import Thread
from multiprocessing.pool import ThreadPool

from zk import ZK, const
import local_config as config
from common import log_event


class AttendDevices(object):
    def __init__(self, devs_file):
        self.all_devices = AttendDevices.get_devices(devs_file)
        self.all_count = len(self.all_devices)
        self.active_devices = {}
        self.active_count = 0
        self.inactive_devices = {}
        self.inactive_count = 0

    def check(self, verbose=True):
        '''Checks all devices passed to constructor as CSV

        :param verbose
        :return dictionary of active devices
        '''
        if verbose:
            print("Checking (" + str(len(self.all_devices)) + ") Devices...")

        pool = ThreadPool(processes=len(self.all_devices))

        async_results = []

        for dev_ip, dev in self.all_devices.items():
            dev_name, dev_pass = dev
            async_results.append(pool.apply_async(AttendDevices.check_device, (dev_ip, dev_name, dev_pass)))

        all_results = []
        for i, res in enumerate(async_results):
            all_results.append(res.get())

        active_devs = {}
        success = 0
        failed = 0
        for dev in all_results:
            if verbose:
                print(dev)
            if '<Success>' in dev:
                success += 1
                active_devs[dev_ip] = (dev_name, dev_pass)
            else:
                failed += 1
        self.active_devices = active_devs
        self.active_count = len(self.active_devices)
        print('Checked <'+str(self.all_count)+'> devices: <'+str(success)+'> Success and <'+str(failed)+'> Failed.')
        return active_devs

    def fetch_raw_attends(self, verbose=True):
        '''Fetches all attendance records from all devices
        :return dictionary of AttendanceAdv Objects
        '''
        if verbose:
            print("Fetching (" + str(len(self.all_devices)) + ") Devices...")

        pool = ThreadPool(processes=len(self.all_devices))

        async_results = []

        for dev_ip, dev in self.all_devices.items():
            dev_name, dev_pass = dev
            async_results.append(pool.apply_async(AttendDevices.get_attendance, (dev_ip, dev_name, dev_pass)))

        all_records = []
        for i, res in enumerate(async_results):
            all_records += res.get()

        return all_records

    def fetch_checkins(self, emp_lookup=[], setnx_callback=None, verbose=True):
        '''Fetch attendances from devices and use an Employee lookup to create ERPNext Check-in records
           to be saved to redis database as JSON str object saved to an ATTEND#<USER_BIO_ID>#<LOG_TIME> key
        '''
        raw_attends = self.fetch_raw_attends()
        check_ins = []
        for rec in raw_attends:
            if rec['user_id'] in emp_lookup.keys():
                check_in_record = {
                    'doctype': 'Employee Checkin',
                    'employee': emp_lookup[rec['user_id']],
                    'time': rec['time'],
                    'log_type': rec['log_type'],
                    'device_id': self.all_devices[rec['device_id']][0],
                    }
                check_ins.append(check_in_record)
                if setnx_callback != None:
                    setnx_callback(rec['user_id'], check_in_record)
            else:
                log_event('Employee on Bio-Device but not on ERPSystem: <' + rec['user_id'] + '>')
        return check_ins

    @staticmethod
    def parse_punch_dir(val):
        device_punch_values_IN = [0, 4]
        device_punch_values_OUT = [1, 5, 255]

        if val in device_punch_values_OUT:
            return 'OUT'
        elif val in device_punch_values_IN:
            return 'IN'
        else:
            return ''

    @staticmethod
    def get_devices(devs_file):
        import csv
        devs = {}
        with open(devs_file, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                devs[row['ip']] = (row['device_id'], row['password'])
        return devs

    @staticmethod
    def check_device(dev_ip, dev_name="", dev_pass=0):
        conn = None
        dev_foot_print = None
        device_timeout = getattr(config, 'device_timeout')
        #zk = ZK(dev_ip, port=4370, timeout=device_timeout, password=dev_pass)
        try:
            # connect to device
            #conn = zk.connect()
            conn = AttendDevices.get_connection(dev_ip, dev_name)

            # disable device, this method ensures no activity on the device while the process is run
            conn.disable_device()

            # get device footprint
            dev_foot_print = '<Success> ' + dev_name + " -- " + dev_ip + " -- " + conn.get_device_name() + " -- " + conn.get_firmware_version() + " -- " +conn.get_serialnumber()

            # re-enable device after all commands already executed
            conn.enable_device()
        except Exception as e:
            event_msg = '<Failed> connecting to: ' + dev_name + ' -- ' + dev_ip + ' -- ' + "Exception : {}".format(e)
            log_event(event_msg)
            return event_msg
        finally:
            if conn:
                conn.disconnect()
        
        return dev_foot_print

    @staticmethod
    def get_connection(dev_ip, dev_name):
        conn = None
        device_timeout = getattr(config, 'device_timeout')
        device_passes = getattr(config, 'device_passes')

        max_attempts = len(device_passes)

        for i in range(0, max_attempts):
            dev_pass_trial = device_passes[i]
            try:
                zk = ZK(dev_ip, port=4370, timeout=device_timeout, password=dev_pass_trial)
                conn = zk.connect()
                if conn:
                    return conn
            except Exception as e:
                event_msg = '<Failed> connecting to: ' + dev_name + ' -- ' + dev_ip + ' -- ' + "Exception : {}".format(e)
                log_event(event_msg)
                continue
        return None
                

    @staticmethod
    def get_attendance(dev_ip, dev_name="", dev_pass=0, verbose=True):
        conn = None
        raw_records = []
        records = []
        device_timeout = getattr(config, 'device_timeout')
        #zk = ZK(dev_ip, port=4370, timeout=device_timeout, password=dev_pass)
        try:
            # connect to device
            #conn = zk.connect()
            conn = AttendDevices.get_connection(dev_ip, dev_name)

            # disable device, this method ensures no activity on the device while the process is run
            conn.disable_device()

            # get device footprint
            dev_foot_print = '<Success> ' + dev_name + " -- " + dev_ip + " -- " + conn.get_device_name() + " -- " + conn.get_firmware_version() + " -- " +conn.get_serialnumber()

            # get attendance records
            raw_records = conn.get_attendance()

            for rec in raw_records:
                records.append({
                        'user_id': rec.user_id,
                        'time': str(rec.timestamp),
                        'log_type': AttendDevices.parse_punch_dir(rec.punch),
                        'device_id': dev_ip,
                    })
            
            # re-enable device after all commands already executed
            conn.enable_device()
        except Exception as e:
            dev_foot_print = '<Failed> fetching attendance from: ' + dev_name + ' -- ' + dev_ip + ' -- ' + "Exception : {}".format(e)
            log_event(dev_foot_print)
        finally:
            if conn:
                conn.disconnect()

        if verbose:
            print(str(datetime.datetime.now()) +"\n"+ dev_foot_print +"\n" + 'Fetched <'+str(len(raw_records))+'> records from device <'+dev_name+':'+dev_ip+'>'+"\n")
        
        return records
