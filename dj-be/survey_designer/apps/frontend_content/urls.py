from rest_framework import routers

from . import views

router = routers.SimpleRouter()
router.register(r"frontend-content", views.FrontendContentViewSet)
urlpatterns = router.urls
