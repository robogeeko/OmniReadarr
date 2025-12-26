from django.contrib import admin

from core.models_processing import ProcessingConfiguration


@admin.register(ProcessingConfiguration)
class ProcessingConfigurationAdmin(admin.ModelAdmin):
    list_display = ["name", "completed_downloads_path", "library_base_path", "enabled"]
    list_filter = ["enabled"]
    fields = [
        "name",
        "completed_downloads_path",
        "library_base_path",
        "calibre_ebook_convert_path",
        "enabled",
    ]

