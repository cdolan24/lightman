# performance_report.py

import sqlite3
from car_database import get_db_path

class PerformanceReport:
    def __init__(self, car_id):
        self.db_path = get_db_path(car_id)

    def generate_report(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT t.name, l.log_data, l.timestamp FROM logs l JOIN tunes t ON l.tune_id = t.id ORDER BY l.timestamp DESC")
        report = c.fetchall()
        conn.close()
        return report

if __name__ == "__main__":
    pr = PerformanceReport(1)
    print("Performance Report:", pr.generate_report())
