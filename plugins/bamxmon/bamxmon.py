# ex: set ts=4 et:

'''
BAMx plugin for rtmbot
listens to Slack message, announce activity and stuff
'''

from collections import defaultdict
import re
import subprocess
import time
import traceback

crontable = [] # don't know how this works...
outputs = [] # append to me to generate output...

channels = {
    u'C04TP1MAC': u'alerts',
    u'C03FDSW2Q': u'devops',
    u'C03G3928S': u'engineering',
    u'C03FDPE88': u'general',
    u'C03JJ7RTM': u'jira',
    u'C03FDPE8J': u'random',
}
chanbyname = {k:v for k,v in channels.items()}

# top-level plugin callback
def process_message(msg):
    try:
        print msg
        if msg.get('type') == u'message': on_message(msg)
    except:
        traceback.print_exc()

def on_message(msg):
    if msg.get('subtype') is None: pass # regular message from human
    elif msg.get('subtype') == u'bot_message': on_botmsg(msg)
    elif msg.get('subtype') == u'message_changed': pass
    elif msg.get('subtype') == u'message_deleted': pass

def on_botmsg(msg):
    # look for pull requests
    attachments = msg.get(u'attachments')
    if attachments:
        pretext = attachments[0].get(u'pretext')
        text = attachments[0].get(u'text')
        # github pull requests
        if pretext:
            if u'Pull request submitted by' in pretext: on_pullrequest_submitted(msg)
            elif u'New comment on pull request' in pretext or u'New comment on commit' in pretext: on_pullrequest_comment(msg)
        if text:
            if u'Merge pull request' in text: on_pullrequest_merged(msg)
            elif u'Pull request re-opened' in text: on_pullrequest_reopened(msg)
            #elif u'Pull request closed' in text: on_pullrequest_closed(msg)
        # alerts
        fallback = attachments[0].get(u'fallback')
        if fallback:
            if u'New alert for' in fallback: on_alert_new(msg)
            elif u'Ended alert for' in fallback: on_alert_ended(msg)

alerts_active = defaultdict(int)

def normalize_alert_key(s):
    return s.replace(u'&gt;', u'>')

def on_alert_new(msg):
    fallback = msg[u'attachments'][0][u'fallback']
    alert_key = re.search(r'New alert for (.+)', fallback).groups(0)[0]
    alert_key_normal = normalize_alert_key(alert_key)
    alerts_active[alert_key_normal] += 1
    # 'Staging: blah...' -> 'Staging'
    # 'Release: blah...' -> 'Release'
    alert_say = alert_key_normal[:alert_key_normal.index(':')] if ':' in alert_key_normal else alert_key_normal
    say('alert. %s' % alert_say)

def on_alert_ended(msg):
    fallback = msg[u'attachments'][0][u'fallback']
    alert_key = re.search(r'Ended alert for (.+)', fallback).groups(0)[0]
    alert_key_normal = normalize_alert_key(alert_key)
    alerts_active[alert_key_normal] = max(0, alerts_active[alert_key_normal] - 1)
    say('alert ended')

def on_pullrequest_submitted(msg):
    pretext = msg[u'attachments'][0][u'pretext']
    username = re.search(r'Pull request submitted by <https?://[^|]+\|([^>]+)>', pretext).groups()[0]
    sayname = username_to_sayname.get(username, username)
    say(u'pull request by %s' % sayname)

def on_pullrequest_reopened(msg):
    pretext = msg[u'attachments'][0][u'text']
    username = re.search(r'Pull request re-opened: <[^>]+> by <https?://[^|]+\|([^>]+)>', pretext).groups()[0]
    sayname = username_to_sayname.get(username, username)
    say(u'pull request by %s' % sayname)

def on_pullrequest_closed(msg):
    pretext = msg[u'attachments'][0][u'text']
    username = re.search(r'Pull request closed: <[^>]+> by <https?://[^|]+\|([^>]+)>', pretext).groups()[0]
    sayname = username_to_sayname.get(username, username)
    say(u'pull request closed')

def on_pullrequest_merged(msg):
    pretext = msg[u'attachments'][0][u'pretext']
    #username = re.search(r'Pull request submitted by <https?://[^|]+\|([^>]+)>', pretext).groups()[0]
    #sayname = username_to_sayname.get(username, username)
    say(u'pull request murged') # XXX: intentional phonetic spelling

def on_pullrequest_comment(msg):
    say(u'pull request comment')

def say(msg):
    subprocess.call([u'say',u'-v',u'Tessa'] + msg.split(u' '))

username_to_sayname = {
    u'Rhathe': 'ramon',
    u'csdev': 'chris',
    u'jwoos': u'jun woo',
    u'pbecotte': u'paul',
    u'rflynn': u'ryan',
    u'vail130': u'vail',
}

'''
Jenkins build failure
{u'attachments': [{u'color': u'd00000', u'fields': [{u'short': False, u'value': u'DOCKER-BUILD-DBS - #908 Failure after 0.71 sec (<http://jenkins.bam-x.com/job/DOCKER-BUILD-DBS/908/|Open>)', u'title': u''}], u'fallback': u'DOCKER-BUILD-DBS - #908 Failure after 0.71 sec (<http://jenkins.bam-x.com/job/DOCKER-BUILD-DBS/908/|Open>)', u'id': 1}], u'text': u'', u'ts': u'1437594175.000122', u'subtype': u'bot_message', u'type': u'message', u'channel': u'C03FDSW2Q', u'bot_id': u'B03FDU74G'}

https://jenkins.bam-x.com/job/DOCKER-BUILD-DBS/rssFailed
https://jenkins.bam-x.com/job/DOCKER-BUILD-DBS/908/consoleText

time="2015-07-20T18:10:15Z" level=fatal msg="Error pushing to registry: Server error: 400 trying to push bamx/postgres:latest manifest"

time="2015-07-20T02:42:51Z" level=fatal msg="Error pushing to registry: Server error: 400 trying head request for bamx/mysql

c2f3c8103eb3: Image already exists

ERROR: Error fetching remote repo 'origin'

nc: connect to 172.17.0.24 port 5432 (tcp) failed: Connection refused
Timed out!

sqlalchemy.exc.IntegrityError:


'''

'''
{u'attachments': [{u'color': u'd00000', u'fields': [{u'short': False, u'value': u'<https://rpm.newrelic.com/accounts/974351/incidents/16014441|Error rate &gt; 10.0%>', u'title': u'Message'}, {u'short': True, u'value': u'Jul 22, 2015 at 13:45:45 UTC', u'title': u'Start Time'}, {u'short': True, u'value': u'Critical', u'title': u'Severity'}], u'fallback': u'[Staging Webapp] New alert for Staging: Error rate &gt; 10.0%', u'id': 1}], u'text': u'[Staging Webapp] New alert for Staging: Error rate &gt; 10.0%', u'ts': u'1437572994.000002', u'subtype': u'bot_message', u'type': u'message', u'channel': u'C04TP1MAC', u'bot_id': u'B04U80VR1'}
{u'attachments': [{u'color': u'59A452', u'fields': [{u'short': False, u'value': u'<https://rpm.newrelic.com/accounts/974351/incidents/16014441|Error rate &gt; 10.0%>', u'title': u'Message'}, {u'short': True, u'value': u'Jul 22, 2015 at 13:45:45 UTC', u'title': u'Start Time'}, {u'short': True, u'value': u'Critical', u'title': u'Severity'}], u'fallback': u'[Staging Webapp] Ended alert for Staging: Error rate &gt; 10.0%', u'id': 1}], u'text': u'[Staging Webapp] Ended alert for
Staging: Error rate &gt; 10.0%', u'ts': u'1437573378.000003', u'subtype': u'bot_message', u'type': u'message', u'channel': u'C04TP1MAC', u'bot_id': u'B04U80VR1'}
'''

'''
{u'attachments': [{u'title': u'#2400 fluentd loses data and is our component', u'color': u'6CC644', u'title_link': u'https://github.com/BAM-X/backend/pull/2400', u'mrkdwn_in': [u'text', u'pretext'], u'pretext': u'[BAM-X/backend] Pull request submitted by <https://github.com/rflynn|rflynn>', u'fallback': u'[BAM-X/backend] <https://github.com/BAM-X/backend/pull/2400|Pull request submitted> by <https://github.com/rflynn|rflynn>', u'id': 1}], u'text': u'', u'ts': u'1437593427.000095', u'subtype': u'bot_message', u'type': u'message', u'channel': u'C03FDSW2Q', u'bot_id': u'B03FBHP4T'}
{u'attachments': [{u'color': u'36a64f', u'fields': [{u'short': False, u'value': u'DOCKER-DEV - #1962 GitHub pull request #2400 of commit 35d8b17a8ae9cee43b11e2c07813fa7fc06a1e73, no merge conflicts. (<http://jenkins.bam-x.com/job/DOCKER-DEV/1962/|Open>)', u'title': u''}], u'fallback': u'DOCKER-DEV - #1962 GitHub pull request #2400 of commit 35d8b17a8ae9cee43b11e2c07813fa7fc06a1e73, no merge conflicts. (<http://jenkins.bam-x.com/job/DOCKER-DEV/1962/|Open>)', u'id': 1}], u'text': u'', u'ts': u'1437593437.000096', u'subtype': u'bot_message', u'type': u'message', u'channel': u'C03FDSW2Q', u'bot_id': u'B03FDU74G'}
'''

