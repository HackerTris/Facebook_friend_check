Facebook_friend_check
=====================

The application in this repository will check which of your Facebook friends have liked your posts, and which of your Facebook friends have commented on your posts.

This application is written in Python, and uses mongo db to store its data.

At this point in time, it is a console application which requires the help of a registiered facebook application.  The registered
application will supply the facebook app id and secret, and a call back URL.  These pieces of data are necessary in 
order to get a valid facebook authorization token.  

There is a little helper app, called facebook__login.py, which will launch this URL so the oAuth sequence can be completed.
The auth token will be in the query string of the call back URL.  This query string is cut and pasted into the 
friend_check operator prompt.  The friend_check application will then run.  In the future, all of this functionality will be 
incorporated into the web applicaiton (indicated by the URL referenced above).

This application makes use of the python facebook api, but I made a slight change to it to accomodate paging data.
