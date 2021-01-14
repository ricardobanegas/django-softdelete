from django.urls import path, include
from softdelete.views import *

urlpatterns = [
    path('changeset/<int:changeset_pk>/undelete/',
        ChangeSetUpdate.as_view(),
        name="softdelete.changeset.undelete"),
    path('changeset/<int:changeset_pk>/',
        ChangeSetDetail.as_view(),
        name="softdelete.changeset.view"),
    path('changeset/',
        ChangeSetList.as_view(),
        name="softdelete.changeset.list"),
]

import sys
if 'test' in sys.argv:
    from django.contrib import admin
    urlpatterns.append(path('admin/', admin.site.urls))
    urlpatterns.append(path('accounts/', include('django.contrib.auth.urls')))
