from rest_framework.routers import DefaultRouter

from .views import ArticleViewSet, ExpandableSectionViewSet, InteractiveElementViewSet


router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
router.register("interactives", InteractiveElementViewSet, basename="interactive")
router.register("sections", ExpandableSectionViewSet, basename="section")

urlpatterns = router.urls
