# -*- coding: utf-8 -*-

from django.conf import settings
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_GET

import math
import oauth2 as oauth
import json
import operator
import re

# Authentication for the Twitter API with oauth2
consumer = oauth.Consumer(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
client = oauth.Client(consumer)

def home(request):    
    return render_to_response('home.html', context_instance=RequestContext(request))


@require_GET
def api_user_timeline(request):
    # only GET requests make it this far thanks to the decorator above
    # return a json with the timeline of a given twitter user (using screen_name=)
    # the result can be sorted by date (default behavior) or by number of retweet (using sorting=byRetweet)
    # the result can be filtered to contain only tweets with photos (using filtering=photos)
    screen_name = request.GET['screen_name']
    if screen_name is not None:
        
        if 'sorting' in request.GET and request.GET['sorting'] == 'byRetweet' :
            # retrieve the full timeline, sort it by retweet_count and keep only the 50 firsts
            user_timeline = get_user_timeline(screen_name, count=0)
            user_timeline.sort(key=operator.itemgetter("retweet_count"), reverse=True)
            user_timeline = user_timeline[:50]
        else :
            # retrieve the user_timeline with the last 50 tweets
            user_timeline = get_user_timeline(screen_name, count=50)

        if 'filtering' in request.GET and request.GET['filtering'] == "photos" :
            # strip away tweets without a media entity from the retrieved timeline
            first_tweet = user_timeline[0]
            
            timeline_with_media = list()
            for tweet in user_timeline:
                if 'media' in tweet['entities'] and 'media_url' in tweet['entities']['media'][0]:
                    timeline_with_media.extend([tweet])
            
            if len(timeline_with_media) == 0:
                # if there is no tweet with pictures in the retrieved timeline, we return a empty tweet except for the user info
                for key in first_tweet:
                    if key != 'user':  first_tweet[key] = ""
                print first_tweet
                timeline_with_media.extend([first_tweet])
                
            json_user_timeline = json.dumps(timeline_with_media)
        
        else :
            json_user_timeline = json.dumps(user_timeline)
        
        return HttpResponse(json_user_timeline, content_type="application/json")
    else:
        return HttpResponseNotFound


@require_GET
def api_user_score(request):
    # only GET requests make it this far thanks to the decorator above
    # return a json with the reputation score of a given twitter user (using screen_name=)
    screen_name = request.GET['screen_name']
    if screen_name is not None:

        ########## 0. retrieve the user timeline
        # In order that the user's ranking is not impacted by its old tweets (everyone can change mood in his life)
        # I am going to consider only the recent tweets
        user_timeline = get_user_timeline(screen_name, count=settings.CONTENT_SCORE_COUNT)
        
        ########## 1. extract followers_count
        followers_count = long(user_timeline[0]['user']['followers_count'])
        
        print 'followers_count_score is ' + str(math.log(followers_count+1))
        
        ########## 2. extract content's score.
        last_tweet_texts = [tweet['text'].lower() for tweet in user_timeline]
        content_score = get_content_score(last_tweet_texts)
        
        print 'content_score is ' + str(content_score)
        
        ########## 3. extract followers' score
        # Based on 1 iteration of a simplified Pagerank algorithm considering only the latest (settings.COUNT_FOR_FOLLOWERS_SCORE) 1-degree nodes relative to the screen_name
        # Considering 5 followers is extremely low in terms of precision but it's fastening up the execution for the sake of this project
        resp, json_followers = client.request('https://api.twitter.com/1.1/followers/list.json?cursor=-1&count='+ str(settings.FOLLOWERS_SCORE_COUNT) +'&screen_name='+ screen_name +'&skip_status=false&include_user_entities=false', "GET")
        followers = json.loads(json_followers)

        followers_score = 0

        for follower in followers['users']:
            followers_score += follower_score(follower)
        
        print 'Followers_score is ' + str(followers_score)
        
        ########## 4. format a simple json to return the score
        score = {'score' : str(score_equation(followers_count, followers_score, content_score))}
        json_score = json.dumps(score)
        return HttpResponse(json_score, content_type="application/json")
    else:
        return HttpResponseNotFound


def get_user_timeline(screen_name, count=0):
    # return the full timeline of the user given as screen_name if count=0. Otherwise return the recent timeline delimited by count
    if count != 0 :
        resp, json_user_timeline = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=' + str(count) + '&screen_name=' + screen_name, "GET")
        return json.loads(json_user_timeline)
    else :    
        resp, json_user_timeline = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=200&screen_name=' + screen_name, "GET")
        user_timeline = json.loads(json_user_timeline)
        
        statuses_count = int(user_timeline[0]['user']['statuses_count'])
        
        while len(user_timeline) < statuses_count:
            # get the last (ie. smallest) id of the returned tweets and substract it by one
            # max_id is going to be fixed as the max cursor for the next request on the user timeline
            max_id = long(user_timeline[-1]['id_str']) - 1
            resp, json_user_timeline = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=200&screen_name=' + screen_name + '&max_id=' + str(max_id), "GET")
            additional_timeline = json.loads(json_user_timeline)
            
            if len(additional_timeline) == 0:
                break
            
            user_timeline.extend(additional_timeline)
            
        return user_timeline


def follower_score(user):
    #print user['screen_name'] + " has " + str(user['friends_count']) + " friends and " + str(user['followers_count']) + " followers"
    content_score = 0
    if 'status' in user :
        content_score = get_content_score([user['status']['text']])

    return float(score_equation(user['followers_count'], 0, content_score)) * settings.FOLLOWERS_SCORE_FACTOR / user['friends_count']

    
def score_equation(followers_count, followers_score, content_score):
    # return the score of a user based on followers_count, followers_score (ie. quality of its followers) and content_score (ie. quality of its tweets)
    return int(max(0, math.ceil(math.log(followers_count+1) + followers_score + content_score)))


def get_content_score(tweet_texts):
    # return the score based on the content of a list of tweet_texts given in input
    # tweet_texts is expected to be a list of non-capitalized texts
    # the value returned can be positive or negative.
    #
    # I used the \b regex for indicating the start or end of a word (such as a white space, a dot, etc.)
    word_count = 0
    
    for text in tweet_texts :
        
        for positive_word in settings.POSITIVE_WORDS :
            if re.search(r'\b' + positive_word + r'\b', text) :
                print '+++ ' + positive_word
                word_count += 1
    
        for negative_word in settings.NEGATIVE_WORDS :
            if re.search(r'\b' + negative_word + r'\b', text) :
                print '--- ' + negative_word
                word_count -= 1
                
    return float(word_count) / len(tweet_texts) * settings.CONTENT_SCORE_FACTOR