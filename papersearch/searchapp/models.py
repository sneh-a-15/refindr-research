# models.py
from django.db import models
from django.contrib.auth.models import User

class BookmarkList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmark_lists')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class BookmarkedPaper(models.Model):
    bookmark_list = models.ForeignKey(BookmarkList, on_delete=models.CASCADE, related_name='bookmarks')
    title = models.CharField(max_length=300)
    author = models.TextField(blank=True)
    link = models.URLField()
    published = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=200, blank=True)
    citation_count = models.IntegerField(default=0)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} in {self.bookmark_list.name}"
