from rest_framework import routers

from .views import SavedSurveyViewset

router = routers.SimpleRouter()
router.register(r"saved-surveys", SavedSurveyViewset, basename="saved_surveys")
urlpatterns = router.urls
