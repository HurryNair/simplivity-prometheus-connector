# -*- coding: utf-8 -*-
"""
Python Class Library for the vcenter Rest API v 2.0.0

Copyright (c) 2021 Hewlett Packard Enterprise, February 22. 2021

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    https://www.gnu.org/licenses/gpl-3.0.en.html

Requirements:


RestAPI Response codes:
    200     OK
    201     Created
    202     Accepted
    204     No Content
    400     Bad Request
    401     Unauthorized
    403     Forbidden
    404     Not Found
    405     Method not allowed
    413     Payload too large
    415     Unsupported Media Type
    500     Internal server error
    502     Bad Gateway
    504     Gateway timeout
    551     No backup found

"""

import requests

DEBUG = False

class vcenter:
    """
    Class vcenter
    Routines for the vcenter REST API
    """
    def __init__(self, url):
        self.url = url                          # base url
        self.session_id = ''                  # session access tokens
        self.headers = {}                       # request headers
        requests.urllib3.disable_warnings()     # suppress http security warning

    def doGet(self, url):
        response = requests.get(url, verify=False, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            pass    # WIP
    
    def doPost(self):
        pass    # WIP

    def doDelete(self):
        pass    # WIP

    def Connect(self, vcenter_username, vcenter_password):
        response = requests.post(self.url, auth = (vcenter_username, vcenter_password), verify = False)
        if response.status_code == 200:
            self.session_id = response.json()['value']
            self.headers = {"vmware-api-session-id": self.session_id}
            return response
        else:
            pass    # WIP

        
