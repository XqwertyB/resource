from django.contrib import admin
from .models import Category, Files, Videos, Recourse, ReviewRecourse, Likes, ReviewVideos

admin.site.register(Category)
@admin.register(Files)
class FilesAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'file', 'recourse']
@admin.register(Videos)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'video_file', 'recourse', 'view_count']
@admin.register(Recourse)
class RecourseAdmin(admin.ModelAdmin):
    list_display = ['category', 'typ', 'user']
@admin.register(ReviewRecourse)
class ReviewRecourseAdmin(admin.ModelAdmin):
    list_display = ['recourse', 'user', 'created_at']
admin.site.register(Likes)
@admin.register(ReviewVideos)
class ReviewVideosAdmin(admin.ModelAdmin):
    list_display = ['video', 'user', 'created_at']





