from django.contrib import admin
from .models import MySubject, Subject, Level, Curriculum, Counties, Constituencies, Wards, Swaps,SwapRequests,Schools,SwapPreference

admin.site.register(MySubject)
admin.site.register(Subject)
admin.site.register(Level)
admin.site.register(Curriculum)
admin.site.register(Counties)
admin.site.register(Constituencies)
admin.site.register(Wards)
admin.site.register(SwapRequests)
admin.site.register(Swaps)
admin.site.register(Schools)
admin.site.register(SwapPreference)