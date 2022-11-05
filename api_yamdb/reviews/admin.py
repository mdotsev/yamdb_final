from django.contrib import admin

from .models import Category, Genre, Review, Title, User


class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'text',
        'title',
        'score',
        'author',
        'pub_date')
    list_editable = ('score',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


admin.site.register(User)
admin.site.register(Category)
admin.site.register(Genre)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Title)
