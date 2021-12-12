import redis
import json
import local_config as config

redis_server = getattr(config, 'redis_server')
redis_port = getattr(config, 'redis_port')

# Yield successive n-sized
# chunks from l.
def divide_chunks(lst, n):
    # looping till length lst
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class EmpDB(object):
    def __init__(self):
        self.redis_conn = redis.Redis('localhost', 6379, 0, decode_responses=True)

    def exists(self, key):
        return self.redis_conn.exists(key)

    def insert_emps(self, all_emps):
        for emp in all_emps:
             self.redis_conn.setnx('EMP:' + emp['attendance_device_id'] + ':' + emp['name'], emp['employee_name'])
        return len(all_emps)

    def get_all_emps(self, invert=False):
        rds_emps = self.redis_conn.keys('EMP:*')

        all_emps = {}
        for rec in rds_emps:
            _, bio_id, db_id = rec.strip("'").split(":")
            all_emps[bio_id] = db_id
        if invert:
            return {v: k for k, v in all_emps.items()}
        return all_emps

    def insert_checkin(self, bio_user_id, record):
        key_name = 'ATTEND'+'#'+str(bio_user_id)+'#'+str(record['time'])
        if not self.redis_conn.exists(key_name) and not self.redis_conn.exists(key_name+'#IMPORTED'):
            return self.redis_conn.setnx('ATTEND'+'#'+str(bio_user_id)+'#'+str(record['time']), json.dumps(record))

    def get_new_checkins(self, per_chunk=0):
        all_keys = self.redis_conn.keys('ATTEND#*')
        new_keys = []

        for rec in all_keys:
            if '#IMPORTED' not in rec:
                new_keys.append(rec)

        new_checkins = self.redis_conn.mget(new_keys)

        checkins = []

        for ck in new_checkins:
            checkins.append(json.loads(ck))

        if per_chunk:
            return list(divide_chunks(checkins, per_chunk))

        return checkins

    def get_imported_checkins(self):
        all_keys = self.redis_conn.keys('ATTEND#*')
        new_keys = []

        for rec in all_keys:
            if '#IMPORTED' in rec:
                new_keys.append(rec)
        return new_keys

    def get_non_imported_checkins(self):
        all_keys = self.redis_conn.keys('ATTEND#*')
        new_keys = []

        for rec in all_keys:
            if '#IMPORTED' not in rec:
                new_keys.append(rec)
        return new_keys

    def delete_keys(self, keys):
        return self.redis_conn.delete(*keys)

    def mark_checkin_imported(self, bio_user_id, log_time):
        old_name = 'ATTEND'+'#'+str(bio_user_id)+'#'+str(log_time)
        new_name = 'ATTEND'+'#'+str(bio_user_id)+'#'+str(log_time)+'#IMPORTED'
        return self.redis_conn.rename(old_name, new_name)

    def match_online_with_db(self, online_emp_checkins):
        ck_diff = []
        new_keys = 0
        emp_lookup = self.get_all_emps(invert=True)
        for emp_checkin in online_emp_checkins:
            if emp_checkin['employee'] in emp_lookup.keys():
                user_id = str(emp_lookup[emp_checkin['employee']])
                log_time = str(emp_checkin['time'])
                key_name = 'ATTEND'+'#'+user_id+'#'+log_time
                if self.exists(key_name):
                    self.mark_checkin_imported(user_id, log_time)
                elif self.exists(key_name+'#IMPORTED'):
                    continue
                else:
                    new_keys += 1
                    self.insert_checkin(user_id, emp_checkin)

