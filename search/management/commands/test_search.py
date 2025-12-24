from django.core.management.base import BaseCommand

from search.models import SearchProvider
from search.providers.registry import get_provider_instance


class Command(BaseCommand):
    help = "Test search providers with real queries"

    def add_arguments(self, parser):
        parser.add_argument(
            "query",
            type=str,
            help="Search query string",
        )
        parser.add_argument(
            "--media-type",
            type=str,
            default="book",
            choices=["book", "audiobook"],
            help="Type of media to search for",
        )
        parser.add_argument(
            "--provider",
            type=str,
            help="Provider name to test (optional, tests all enabled if not specified)",
        )

    def handle(self, *args, **options):
        query = options["query"]
        media_type = options["media_type"]
        provider_name = options.get("provider")

        if provider_name:
            try:
                provider_model = SearchProvider.objects.get(name=provider_name)
            except SearchProvider.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Provider '{provider_name}' not found")
                )
                return
            providers = [provider_model]
        else:
            providers = SearchProvider.objects.filter(
                enabled=True,
                supports_media_types__contains=[media_type],
            ).order_by("priority")

        if not providers:
            self.stdout.write(
                self.style.WARNING("No enabled providers found for this media type")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Searching for '{query}' (media_type: {media_type})")
        )
        self.stdout.write("")

        for provider_model in providers:
            self.stdout.write(self.style.SUCCESS(f"\n--- {provider_model.name} ---"))

            try:
                provider = get_provider_instance(provider_model)
                results = provider.search(query, media_type, language=None)

                if not results:
                    self.stdout.write(self.style.WARNING("  No results found"))
                    continue

                self.stdout.write(
                    self.style.SUCCESS(f"  Found {len(results)} results:")
                )
                self.stdout.write("")

                for i, result in enumerate(results[:5], 1):
                    self.stdout.write(f"  {i}. {result.title}")
                    if result.authors:
                        self.stdout.write(f"     Authors: {', '.join(result.authors)}")
                    if result.isbn13:
                        self.stdout.write(f"     ISBN-13: {result.isbn13}")
                    elif result.isbn:
                        self.stdout.write(f"     ISBN: {result.isbn}")
                    if result.publication_date:
                        self.stdout.write(
                            f"     Published: {result.publication_date.year}"
                        )
                    if result.publisher:
                        self.stdout.write(f"     Publisher: {result.publisher}")
                    if result.page_count:
                        self.stdout.write(f"     Pages: {result.page_count}")
                    if result.cover_url:
                        self.stdout.write(f"     Cover: {result.cover_url}")
                    self.stdout.write("")

                if len(results) > 5:
                    self.stdout.write(
                        self.style.WARNING(f"  ... and {len(results) - 5} more results")
                    )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error: {type(e).__name__}: {e}"))
