# ERPNext Connection Parameters
api_key = '9b75f7a2ff9534e'
api_secret = '11e9f896bb30e02'
erp_url = 'https://zck21.2srv.me'

# Redis Server Connection Parameters
redis_server = 'localhost'
redis_port = 6379

# Biometric Attendance Devices
device_timeout = 60
devices_csv = "/home/erpnext-attend-sync/bio_devices_ips.csv"
device_passes = [0, 88, 2021]

# Log file name
log_file = 'event.log'

# employee checkins to push in each request
checkins_per_request = 200

# max connections to open with ERPNext simultaneously
max_simult_requests = 5

# max iterations per task run (so the total final records will be = checkins_per_request * max_simult_requests * max_iterations_per_task)
max_iterations_per_task = 2
