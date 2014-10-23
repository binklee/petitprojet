# -*- coding: utf-8 -*-

from django.conf import settings
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.views.decorators.http import require_GET

import oauth2 as oauth
import json

# Authentication for the Twitter API with oauth2
consumer = oauth.Consumer(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
client = oauth.Client(consumer)


def home(request):    
    return render_to_response('home.html', context_instance=RequestContext(request))

@require_GET
def api_user_timeline(request):
    # only GET requests make it this far thanks to the decorator above
    screen_name = request.GET['screen_name']
    if screen_name is not None:
        resp, content = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name='+screen_name, "GET")
        return HttpResponse(content, content_type="application/json")