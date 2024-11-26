import uuid

from django.db import models

from users.models import User


class BaseModel(models.Model):
    """
    - Bu model har doim id, created_at va updated_at fieldlarni qayta yozmasdan har qanday modelda inherit qilib ishlash imkonini beruvchi class.

    - Bu class modelda yaratilmaydi sababi abstract=True deyilgani uchun.

    - Demak, qayta qayta yuqoridagi filedlarni yozmaslik uchun ishlab chiqilgan model

    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(BaseModel):
    name = models.CharField("Kategoriya nomi", max_length=200)

    def __str__(self):
        return self.name



# class Sub_Category(BaseModel):
#     name = models.CharField("Sub kategoriya nomi", max_length=200)
#     sub_category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="sub_category")
#
#     def __str__(self):
#         return self.name


# class Category(models.Model, BaseModel):
#     name = models.CharField("Resurslar nomi", max_length=200)
#     sub_category = models.ForeignKey(Sub_Category, on_delete=models.CASCADE)
#
#     def __str__(self):
#         return self.name
#
#
#
# class Files(BaseModel):
#     name = models.CharField(max_length=200)
#     file = models.FileField("Fayl", upload_to='files/')
#
#     def __str__(self):
#         return self.name
#
#
# class Videos(BaseModel):
#     name = models.CharField(max_length=200)
#     video_file = models.FileField("Video Fayl", upload_to="videos/", )
#
#     def __str__(self):
#         return self.name
#
# TYPE = (
#     ("Presentation", "Taqdimot"),
#     ("Scientific work", "Ilmiy ish"),
#     ("Diploma work", "Diplom ishi"),
#     ("Book", "Kitob"),
# )
#
#
# class Recourse(BaseModel):
#     sub_category = models.ForeignKey(Sub_Category, on_delete=models.CASCADE, related_name='category')
#     file = models.ForeignKey(Files, on_delete=models.CASCADE, related_name='files')
#     video = models.ForeignKey(Videos, on_delete=models.CASCADE, related_name='videos')
#     typ = models.CharField("Resurs turi", choices=TYPE, max_length=50)
#     info = models.TextField('Malumot')
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#
#     def __str__(self):
#         return f"{self.typ} - {self.sub_category.name} "




class Files(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    file = models.FileField("Fayl", upload_to='files/')

    def __str__(self):
        return self.name


class Videos(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    video_file = models.FileField("Video Fayl", upload_to="videos/", )

    def __str__(self):
        return self.name

TYPE = (
    ("presentation", "Taqdimot"),
    ("scientific", "Ilmiy ish"),
    ("diplom", "Diplom ishi"),
    ("book", "Kitob"),
)


class Recourse(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='category')
    typ = models.CharField("Resurs turi", choices=TYPE, max_length=50)
    info = models.TextField('Malumot')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.typ} - {self.category.name} "



class RecViews(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rec = models.ForeignKey(Recourse, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'rec')

class ReviewRecourse(models.Model):
    recourse = models.ForeignKey(Recourse, on_delete=models.CASCADE, related_name='reviews')  # Ресурс, к которому относится отзыв
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  
    def __str__(self):
        return f"Review for {self.recourse} by {self.user.username}"

class Likes(models.Model):
    ip = models.CharField('IP', max_length=100)
    resource = models.ForeignKey(Recourse, on_delete=models.CASCADE)
