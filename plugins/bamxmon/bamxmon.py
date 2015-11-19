# ex: set ts=4 et:

'''
BAMx plugin for rtmbot
listens to Slack message, announce activity and stuff
'''

# XXX: needs a nice rewrite

import platform
import re
import subprocess
import traceback
import urllib2
from collections import defaultdict

crontable = []  # don't know how this works...
outputs = []  # append to me to generate output...

channels = {
    u'C04TP1MAC': u'alerts',
    u'C03FDSW2Q': u'devops',
    u'C03G3928S': u'engineering',
    u'C03FDPE88': u'general',
    u'C03JJ7RTM': u'jira',
    u'C03FDPE8J': u'random',
}
chanbyname = {k: v for k, v in channels.items()}


# top-level plugin callback
def process_message(msg):
    try:
        print msg
        if msg.get('type') == u'message': on_message(msg)
    except:
        traceback.print_exc()


def on_message(msg):
    if msg.get('subtype') is None:
        pass  # regular message from human
    elif msg.get('subtype') == u'bot_message':
        on_botmsg(msg)
    elif msg.get('subtype') == u'message_changed':
        pass
    elif msg.get('subtype') == u'message_deleted':
        pass


def on_botmsg(msg):
    # look for pull requests
    attachments = msg.get(u'attachments')

    if is_jenkins_failure(msg):
        faulty_component = jenkins_failure_forensic_blame(jenkins_failure_joburl(msg))
        build_error(faulty_component)
    elif attachments:
        pretext = attachments[0].get(u'pretext')
        text = attachments[0].get(u'text')
        # github pull requests
        if pretext:
            if u'Pull request submitted by' in pretext:
                on_pullrequest_submitted(msg)
            elif u'New comment on pull request' in pretext or u'New comment on commit' in pretext:
                on_pullrequest_comment(msg)
        if text:
            if u'Merge pull request' in text:
                on_pullrequest_merged(msg)
            elif u'Pull request re-opened' in text:
                on_pullrequest_reopened(msg)
            # elif u'Pull request closed' in text: on_pullrequest_closed(msg)
        # alerts
        fallback = attachments[0].get(u'fallback')
        if fallback:
            if u'New alert for' in fallback:
                on_alert_new(msg)
            elif u'Ended alert for' in fallback:
                on_alert_ended(msg)


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
    # username = re.search(r'Pull request submitted by <https?://[^|]+\|([^>]+)>', pretext).groups()[0]
    # sayname = username_to_sayname.get(username, username)
    say(u'pull request murged')  # XXX: intentional phonetic spelling


def on_pullrequest_comment(msg):
    try:
        pretext = msg[u'attachments'][0][u'pretext']
        # [BAM-X/backend] New comment on commit <https://github.com/BAM-X/backend/pull/3376#discussion_r45412760|6b2f53e>
        pr_num = re.search(r'New comment on commit <https?://github.com/BAM-X/backend/pull/(\d+).*', pretext).groups()[
            0]
        username = re.search(r'Comment by (.+)\n', msg[u'attachments'][0][u'title']).groups()[0]
        if msg[u'attachments'][0][u'text'] == u'#test':  # special Jenkins convention
            say(u'%s is re-running P R %s' % (' '.join(str(pr_num)), username_to_sayname.get(username)))
        else:
            say(u'%s commented on pull request %s' % (username_to_sayname.get(username), ' '.join(str(pr_num))))
    except:
        pass


def say(msg, voice=u'Tessa'):
    system = platform.system()
    if system == 'Linux':
        subprocess.call([u'espeak', u'-s', u'200', u'-v', u'en+f2'] + msg.split(u' '))
    elif system == 'Darwin':
        subprocess.call([u'say', u'-v', voice] + msg.split(u' '))


username_to_sayname = {
    u'Rhathe': u'ramon',
    # u'Rhathe': {'default': u'ramon', 'espeak': u'ra-moan'},
    u'csdev': u'chris',
    u'jwoos': u'jun woo',
    u'pbecotte': u'paul',
    u'rflynn': u'ryan',
    u'vail130': u'vail',
    u'stupschwartz': u'stu',
}


class BuildComponent(object):
    UNKNOWN = 1
    DOCKERHUB = 2
    POSTGRESQL = 3
    GITHUB = 4


def build_error(component):
    if component == BuildComponent.DOCKERHUB:
        build_error_dockerhub()
    elif component == BuildComponent.POSTGRESQL:
        build_error_postgresql()
    elif component == BuildComponent.GITHUB:
        build_error_github()
    else:
        say('error')


def build_error_dockerhub():
    say('docker hub')


def build_error_postgresql():
    say('post gress')


def build_error_github():
    say('git hub')


def is_jenkins_failure(msg):
    try:
        return (
            msg[u'type'] == u'message'
            and msg[u'subtype'] == u'bot_message'
            and re.search(r'#\d+ Failure after.*jenkins.bam-x.com/', msg[u'attachments'][0][u'fields'][0][u'value'])
        )
    except:
        return False


def jenkins_failure_joburl(msg):
    try:
        return re.search(r'#\d+.*<(http[^|]+)', msg[u'attachments'][0][u'fields'][0][u'value']).groups()[0]
    except:
        pass


def jenkins_failure_forensic_blame(joburl):
    try:
        url = joburl + u'consoleText'
        # https://hue:peSYPN0g6uy4iX@jenkins.bam-x.com/...
        req = urllib2.Request(url)
        txt = urllib2.urlopen(req).read()
        if is_it_dockerhub(txt):
            return BuildComponent.DOCKERHUB
        elif is_it_github(txt):
            return BuildComponent.GITHUB
        elif is_it_postgresql(txt):
            return BuildComponent.POSTGRESQL
        return BuildComponent.UNKNOWN
    except Exception as e:
        print e


def is_it_dockerhub(consoletext):
    return (
        u'Error pushing to registry: Server error' in consoletext
        or u'Image already exists' in consoletext
        or u'Image push failed' in consoletext
        or bool(re.search(r'docker.*i/o timeout', consoletext))
    )


def is_it_github(consoletext):
    return (
        u'ERROR: Error fetching remote repo' in consoletxt
    )


def is_it_postgresql(consoletext):
    return (
        bool(
            re.search('^nc: connect to (?P<host_or_ip>\S+) port 5432 \(tcp\) failed: Connection refused\r?\nTimed out!',
                      consoletext))
    )


'''
Jenkins build failure
{u'attachments': [{u'color': u'd00000', u'fields': [{u'short': False, u'value': u'DOCKER-BUILD-DBS - #908 Failure after 0.71 sec (<http://jenkins.bam-x.com/job/DOCKER-BUILD-DBS/908/|Open>)', u'title': u''}], u'fallback': u'DOCKER-BUILD-DBS - #908 Failure after 0.71 sec (<http://jenkins.bam-x.com/job/DOCKER-BUILD-DBS/908/|Open>)', u'id': 1}], u'text': u'', u'ts': u'1437594175.000122', u'subtype': u'bot_message', u'type': u'message', u'channel': u'C03FDSW2Q', u'bot_id': u'B03FDU74G'}

https://jenkins.bam-x.com/job/DOCKER-BUILD-DBS/rssFailed
https://jenkins.bam-x.com/job/DOCKER-BUILD-DBS/908/consoleText

time="2015-07-20T18:10:15Z" level=fatal msg="Error pushing to registry: Server error: 400 trying to push bamx/postgres:latest manifest"

time="2015-07-20T02:42:51Z" level=fatal msg="Error pushing to registry: Server error: 400 trying head request for bamx/mysql

c2f3c8103eb3: Image already exists

c2f3c8103eb3: Image push failed

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
