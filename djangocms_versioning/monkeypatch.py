from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.utils.functional import cached_property

from cms.models import titlemodels
from cms.operations import ADD_PAGE_TRANSLATION, CHANGE_PAGE_TRANSLATION
from cms.signals import post_obj_operation
from cms.toolbar import toolbar

from .constants import PUBLISHED
from .models import Version
from .plugin_rendering import VersionRenderer


def content_renderer(self):
    return VersionRenderer(request=self.request)


@receiver(post_obj_operation)
def pre_page_operation_handler(sender, **kwargs):
    operations = (ADD_PAGE_TRANSLATION, CHANGE_PAGE_TRANSLATION)
    operation_type = kwargs['operation']

    if operation_type not in operations:
        return

    page = kwargs['obj']
    language = kwargs['language']
    cms_extension = apps.get_app_config('djangocms_versioning').cms_extension
    versionable_item = cms_extension.versionables_by_grouper[page.__class__]
    page_contents = (
        versionable_item
        .for_grouper(page)
        .filter(language=language)
        .values_list('pk', flat=True)
    )
    content_type = ContentType.objects.get_for_model(page_contents.model)
    has_published = (
        Version
        .objects
        .filter(
            state=PUBLISHED,
            content_type=content_type,
            object_id__in=page_contents,
        )
        .exists()
    )

    if not has_published:
        page.update_urls(language, path=None)
        page._update_url_path_recursive(language)
        page.clear_cache(menu=True)


pagecontent_unique_together = tuple(
    set(titlemodels.PageContent._meta.unique_together) -
    set((('language', 'page'), ))
)

toolbar.CMSToolbar.content_renderer = cached_property(content_renderer)
titlemodels.PageContent._meta.unique_together = pagecontent_unique_together