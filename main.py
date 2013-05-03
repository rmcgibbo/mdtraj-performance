#!/usr/bin/env python

##############################################################################
# Imports
##############################################################################

import webapp2
from StringIO import StringIO
import csv
import json
import time
import gviz_api
from datetime import datetime
from google.appengine.ext import db

##############################################################################
# Models
##############################################################################

class Report(db.Model):
    time = db.DateTimeProperty()
    revision = db.StringProperty()
    
    @classmethod
    def from_json(cls, jsonstring):
        return cls(
            time = isoformat_to_date(jsonstring['time']),
            revision = jsonstring['revision']
        )


class Test(db.Model):
    duration = db.FloatProperty()
    doc = db.StringProperty()
    report = db.ReferenceProperty(Report)
    id = db.StringProperty()
    
    @classmethod
    def from_json(cls, jsonstring):
        return cls(
            duration = jsonstring['duration'],
            doc = jsonstring['doc'],
            id = jsonstring['id']
        )

##############################################################################
# Utilities
##############################################################################

def isoformat_to_date(isodatestring):
    """Turn a isodatestring into a datetime object
    Example
    -------
    >>> isoformat_to_date("2013-05-02T20:30:42.303176")
    
    """
    # ignoring the milliseconds here
    if '.' in isodatestring:
        isodatestring, fraction = isodatestring.split('.')
    dt = datetime.strptime(isodatestring, "%Y-%m-%dT%H:%M:%S")
    return dt

##############################################################################
# Globals
##############################################################################

page_template = """
<html>
  <script src="https://www.google.com/jsapi" type="text/javascript"></script>
  <script>
    google.load('visualization', '1', {packages:['corechart', 'table']});

    google.setOnLoadCallback(drawTable);
    function drawTable() {
      %(jscode)s
      var chart = new google.visualization.ScatterChart(document.getElementById('chart_div'));
      chart.draw(data, {
          title: 'MDTraj Performance',
          pointSize: 5,
      });
      
      var table = new google.visualization.Table(document.getElementById('table_div'));
      table.draw(data, {showRowNumber: true});
    }
  </script>

  <body>
    <div id="chart_div"></div>
    <div id="table_div"></div>
  </body>
</html>
"""

##############################################################################
# Handlers
##############################################################################

class MainHandler(webapp2.RequestHandler):
    def get(self):
        columns = {'time': ('number', 'Time')}
        data = []
        
        for report in Report.all().run(limit=100):
            tests = report.test_set.run()
            row = {'time': time.mktime(report.time.timetuple())}
            for t in tests:
                columns[t.id] = ("number", t.id)
                row[t.id] = t.duration
            data.append(row)

        table = gviz_api.DataTable(columns)
        table.LoadData(data)

        # we want time to be in the beginning, so that it's the x axis
        column_order = ['time']
        column_order.extend([k for k in columns.keys() if k != 'time'])

        jscode = table.ToJSCode("data", columns_order=column_order)
        self.response.write(page_template % vars())

    def post(self):
        j = json.loads(self.request.get('fileupload'))
        report = Report.from_json(j)
        report.put()
        
        for testj in j['tests']:
            t = Test.from_json(testj)
            t.report = report
            t.put()

        self.response.write('Thanks!')

class DumpHandler(webapp2.RequestHandler):
    def get(self):
        buf = StringIO()
        c = csv.writer(buf)
        c.writerow(['Time', 'Git Revision', 'Duration', 'Docstring', 'Test ID'])
        for report in Report.all().run():
            for test in report.test_set.run():
                c.writerow([report.time, report.revision, test.duration, test.doc, test.id])
    
        self.response.headers['Content-Type'] = 'text/csv'
        self.response.write(buf.getvalue())
    

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/dump', DumpHandler),
], debug=True)
