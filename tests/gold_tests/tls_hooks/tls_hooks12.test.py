'''
Test a combination of delayed and immediate preaccept callbacks
'''
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import re

Test.Summary = '''
Test different combinations of TLS handshake hooks to ensure they are applied consistently.
'''

Test.SkipUnless(Condition.HasProgram("grep", "grep needs to be installed on system for this test to work"))

ts = Test.MakeATSProcess("ts", select_ports=False)
server = Test.MakeOriginServer("server")
request_header = {"headers": "GET / HTTP/1.1\r\nHost: www.example.com\r\n\r\n", "timestamp": "1469733493.993", "body": ""}
# desired response form the origin server
response_header = {"headers": "HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n", "timestamp": "1469733493.993", "body": ""}
server.addResponse("sessionlog.json", request_header, response_header)

ts.addSSLfile("ssl/server.pem")
ts.addSSLfile("ssl/server.key")

ts.Variables.ssl_port = 4443
ts.Disk.records_config.update({
    'proxy.config.diags.debug.enabled': 1,
    'proxy.config.diags.debug.tags': 'ssl_hook_test',
    'proxy.config.ssl.server.cert.path': '{0}'.format(ts.Variables.SSLDir),
    'proxy.config.ssl.server.private_key.path': '{0}'.format(ts.Variables.SSLDir),
    # enable ssl port
    'proxy.config.http.server_ports': '{0}:ssl'.format(ts.Variables.ssl_port),
    'proxy.config.ssl.client.verify.server':  0,
    'proxy.config.ssl.server.cipher_suite': 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:AES128-GCM-SHA256:AES256-GCM-SHA384:ECDHE-RSA-RC4-SHA:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:RC4-SHA:RC4-MD5:AES128-SHA:AES256-SHA:DES-CBC3-SHA!SRP:!DSS:!PSK:!aNULL:!eNULL:!SSLv2',
})

ts.Disk.ssl_multicert_config.AddLine(
    'dest_ip=* ssl_cert_name=server.pem ssl_key_name=server.key'
)

ts.Disk.remap_config.AddLine(
    'map https://example.com:4443 http://127.0.0.1:{0}'.format(server.Variables.Port)
)

Test.prepare_plugin(os.path.join(Test.Variables.AtsTestToolsDir, 'plugins', 'ssl_hook_test.cc'), ts, '-p=2 -d=1')

tr = Test.AddTestRun("Test combination of delayed and immediate preaccept hook2")
tr.Processes.Default.StartBefore(server)
tr.Processes.Default.StartBefore(Test.Processes.ts, ready=When.PortOpen(ts.Variables.ssl_port))
tr.StillRunningAfter = ts
tr.StillRunningAfter = server
tr.Processes.Default.Command = 'curl -k -H \'host:example.com:{0}\' https://127.0.0.1:{0}'.format(ts.Variables.ssl_port)
tr.Processes.Default.ReturnCode = 0
tr.Processes.Default.Streams.stdout = "gold/preaccept-1.gold"

ts.Streams.stderr = "gold/ts-preaccept-delayed-1-immdate-2.gold"

# Not going to check for number of times the message appears.  With the current test framework
# a probing TCP connection is made to test that the port is listening.  The entire preaccept hook
# sequence may appear on that probe.  Or it may not.  If we move away from the probe connection
# we can check for the right number of each message.
#preacceptstring0 = "Pre accept delay callback 0"
#ts.Streams.All = Testers.ContainsExpression(
#    "\A(?:(?!{0}).)*{0}.*({0})?(?!.*{0}).*\Z".format(preacceptstring0), "Pre accept message appears only once or twice", reflags=re.S | re.M)
#preacceptstring1 = "Pre accept callback 0"
#ts.Streams.All = Testers.ContainsExpression(
#    "\A(?:(?!{0}).)*{0}.*({0})?(?!.*{0}).*\Z".format(preacceptstring1), "Pre accept message appears only once or twice", reflags=re.S | re.M)
#preacceptstring2 = "Pre accept callback 1"
#ts.Streams.All = Testers.ContainsExpression(
#    "\A(?:(?!{0}).)*{0}.*({0})?(?!.*{0}).*\Z".format(preacceptstring2), "Pre accept message appears only once or twice", reflags=re.S | re.M)

tr.Processes.Default.TimeOut = 5
tr.TimeOut = 5
