from django.conf.urls.defaults import patterns, include, url

# here we handle all the URL redirections

urlpatterns = patterns('',
    url(r'^$', 'petitprojetapp.views.home'),
    url(r'^index.html$', 'petitprojetapp.views.home'),
    url(r'^api/user_timeline.json$', 'petitprojetapp.views.api_user_timeline'),
    url(r'^api/user_score.json$', 'petitprojetapp.views.api_user_score'),
)
