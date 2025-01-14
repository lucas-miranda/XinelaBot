import json
import os
from datetime import datetime, timedelta, date

import pytz


class DataHandler:
    timezone = pytz.timezone('America/Sao_Paulo')

    def __init__(self, json_file='Data.json'):
        self.json_file = json_file
        self.dict = self.load_from_json()
        self.__validate_data()

    def reset(self):
        self.dict = self.__generate_data()
        self.save_to_json()

    def load_from_json(self):
        if os.path.isfile(self.json_file):
            with open(self.json_file) as file:
                return json.load(file)

        return None

    def save_to_json(self):
        with open(self.json_file, 'w') as file:
            json.dump(self.dict, file)

    def add(self, time: str, user_id: int):
        if time not in self.dict['times']:
            self.dict['times'][time] = []
        if user_id in self.dict['times'][time]:
            self.dict['times'][time].remove(user_id)
        else:
            self.dict['times'][time].append(user_id)
            self.dict['times'][time] = list(set(self.dict['times'][time]))
        self.save_to_json()
        return len(self.dict['times'][time])

    def add_timeslot(self, timeslot: str):
        if timeslot not in self.dict['times']:
            self.dict['times'][timeslot] = []
        self.save_to_json()

    def get_timeslots(self):
        return list(self.dict['times'].keys())

    def get_users_at_time(self, time):
        if time in self.dict['times']:
            return ', '.join(f'<@{user}>' for user in self.dict['times'][time])
        else:
            return "No users at this time."

    def get_users_list_at_time(self, time):
        if time in self.dict['times']:
            return list((user for user in self.dict['times'][time]))
        else:
            return None

    def add_job(self, run_date, channel_id, user_id, job_id):
        self.dict['jobs'].append({
            'job_id': job_id,
            'run_time': run_date.isoformat(),
            'user_id': user_id,
            'channel_id': channel_id
        })
        self.save_to_json()

    def remove_job(self, job_id):
        self.dict['jobs'] = [job for job in self.dict['jobs'] if job['job_id'] != job_id]
        self.save_to_json()

    def most_votes(self):
        most_voted_time = None
        most_votes = 0

        for time, votes in self.dict["times"].items():
            vote_count = len(votes)
            if vote_count > most_votes:
                most_votes = vote_count
                most_voted_time = time

        unix_timestamp = self.time_to_unix_timestamp(most_voted_time)

        return most_voted_time, unix_timestamp

    @staticmethod
    def time_to_unix_timestamp(time):
        if time:
            hour, minute = map(int, time.split('h'))
            now = datetime.now(DataHandler.timezone)
            selected_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if selected_time < now:
                selected_time += timedelta(days=1)
            unix_timestamp = int(selected_time.timestamp())
        else:
            unix_timestamp = None
        return unix_timestamp

    def __generate_data(self):
        date_now = datetime.now(DataHandler.timezone).date()

        data = {
            "timestamp": date_now.isoformat(),
            "times": {},
            "jobs": []
        }

        from_hour = 9
        to_hour = 23

        for h in range(from_hour, to_hour + 1):
            data["times"]["{0}h00".format(h)] = []

        return data

    def __validate_data(self):
        if not self.dict:
            self.reset()
            return

        # verify if date is from the same day
        # otherwise regerate data
        date_now = datetime.now(DataHandler.timezone).date()

        if "timestamp" in self.dict:
            # ensure we're at the same day
            time_delta = date_now - date.fromisoformat(self.dict["timestamp"])

            if time_delta.days > 0:
                # it's another day already
                self.reset()
        else:
            # fill timestamp data
            self.dict["timestamp"] = date_now.isoformat()
            self.save_to_json()
