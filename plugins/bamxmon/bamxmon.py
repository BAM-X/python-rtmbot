# ex: set ts=4 et:

'''
BAMx plugin for rtmbot
listens to Slack message, announce activity and stuff
'''

import re
import subprocess
import time
import traceback

crontable = [] # don't know how this works...
outputs = [] # append to me to generate output...

'''
channels = {
    u'C04TP1MAC': u'alerts',
    u'C03FDSW2Q': u'devops',
    u'C03G3928S': u'engineering',
    u'C03FDPE88': u'general',
    u'C03JJ7RTM': u'jira',
    u'C03FDPE8J': u'random',
}
chanbyname = {k:v for k,v in channels.items()}
'''

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
        if pretext:
            if u'Pull request submitted by' in pretext: on_pullrequest_submitted(msg)
            elif u'Merge pull request' in pretext: on_pullrequest_merged(msg)
            elif u'New comment on pull request' in pretext: on_pullrequest_comment(msg)
        elif text:
            if u'Pull request re-opened' in text: on_pullrequest_reopened(msg)
            elif u'Pull request closed' in text: on_pullrequest_closed(msg)

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
}

