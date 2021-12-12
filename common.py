import datetime
import local_config as config

def log_event(msg, event_type='ERROR', debug=False):
    log_file = getattr(config, 'log_file')
    event_msg = event_type + ' --- ' + msg + ' --- ' + str(datetime.datetime.now()) + "\n"
    with open(log_file, mode='a', encoding='UTF-8') as file:
        file.write(event_msg)
        if debug:
            print(event_msg)
    return True