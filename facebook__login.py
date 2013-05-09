""" Get Access token for use by friend_check.py.

This module gets the access token, using the OAuth 2.0 negotiation process.  It then
allows the access token to be written to a file for use in friend_check.py.

When this funcitonality is hosted in the cloud, this maodule will be substantially
reworked and integrated into the web application.

The current sequence of steps (for running the app on a console) is to run this module,
which will cause the web app registered to Facebook to opened.  The access token
will be in the query string.  You can tell what it is by inspection. This access token is
then cut and pasted into the prompt issued by this console app.  This app then writes
the token to a file.  The file is read by friend_check.py.

"""


import os
import sys
import webbrowser
import urllib


def login():

    CLIENT_ID = "232143230258494"
    REDIRECT_URI = "https://agile-crag-1407.herokuapp.com/"
    EXTENDED_PERMS = [
        'user_about_me',
        'user_activities',
        'user_actions.news',
        'user_actions.video',
        'friends_activities',
        'friends_actions.video',
        'friends_likes',
        'friends_actions.news',
        'user_birthday',
        'user_events',
        'friends_events',
        'user_likes',
        'user_photos',
        'friends_photos',
        'user_status',
        'friends_status',
        'user_videos',
        'friends_videos',
        'offline_access',
        'read_friendlists',
        'read_stream']

    args = dict(client_id=CLIENT_ID,redirect_uri=REDIRECT_URI,scope=','.join(EXTENDED_PERMS),
                type='user_agent',display='popup')
                                                                           
    webbrowser.open('https://graph.facebook.com/oauth/authorize?' + urllib.urlencode(args))
    access_token = raw_input('Enter your access_token: ')
    if not os.path.isdir('out'):
        os.mkdir('out')
    filename = os.path.join('out','facebook.access_token')
    f = open(filename,'w')
    f.write(access_token)
    f.close()
    print >> sys.stderr,"Access token stored to local file: 'out/facebook.access_token'"
    return access_token

if __name__ == '__main__':
    login()
                                                            
        
