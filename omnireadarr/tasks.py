import dramatiq


@dramatiq.actor
def example_task(value: int) -> int:
    """Example task that doubles a number."""
    result = value * 2
    print(f"Processing task: {value} * 2 = {result}")
    return result


@dramatiq.actor(max_retries=3)
def process_media(media_id: int) -> None:
    """Process media item."""
    print(f"Processing media ID: {media_id}")
