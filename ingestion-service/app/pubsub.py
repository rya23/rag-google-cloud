"""Pub/Sub utilities for event-driven ingestion job processing."""

import json
import logging
from typing import Callable, Optional
from concurrent.futures import TimeoutError

from google.cloud import pubsub_v1
from . import config

logger = logging.getLogger(__name__)


def get_publisher() -> pubsub_v1.PublisherClient:
    """Get a Pub/Sub publisher client."""
    return pubsub_v1.PublisherClient()


def get_subscriber() -> pubsub_v1.SubscriberClient:
    """Get a Pub/Sub subscriber client."""
    return pubsub_v1.SubscriberClient()


def publish_ingestion_job(job_id: int, filename: str, storage_path: str) -> bool:
    """
    Publish an ingestion job message to Pub/Sub topic.

    Args:
        job_id: ID of the ingestion job
        filename: Original filename uploaded
        storage_path: GCS path where file is stored (gs://bucket/path)

    Returns:
        True if published successfully, False otherwise
    """
    if not config.GCP_PROJECT_ID:
        logger.warning("GCP_PROJECT_ID not configured, skipping Pub/Sub publish")
        return False

    try:
        publisher = get_publisher()
        topic_path = publisher.topic_path(
            config.GCP_PROJECT_ID, config.PUBSUB_TOPIC_NAME
        )

        message_data = {
            "job_id": job_id,
            "filename": filename,
            "storage_path": storage_path,
        }

        # Publish the message
        future = publisher.publish(
            topic_path,
            data=json.dumps(message_data).encode("utf-8"),
        )

        # Wait for the publish to complete (with timeout)
        message_id = future.result(timeout=5.0)
        logger.info(f"Published job {job_id} to Pub/Sub (message_id={message_id})")
        return True

    except TimeoutError:
        logger.error(f"Timeout publishing job {job_id} to Pub/Sub")
        return False
    except Exception as e:
        logger.error(f"Failed to publish job {job_id} to Pub/Sub: {e}")
        return False


def subscribe_to_ingestion_jobs(
    callback: Callable[[dict], None],
    timeout: Optional[float] = None,
) -> None:
    """
    Subscribe to ingestion job messages and process them.

    This function blocks indefinitely (or until timeout), calling the callback
    for each message received on the subscription.

    Args:
        callback: Async function that accepts a message dict with keys:
                 job_id, filename, storage_path
        timeout: Optional timeout in seconds. If None, listens forever.
    """
    if not config.GCP_PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID not configured")

    subscriber = get_subscriber()
    subscription_path = subscriber.subscription_path(
        config.GCP_PROJECT_ID,
        config.PUBSUB_SUBSCRIPTION_NAME,
    )

    def message_callback(message: pubsub_v1.subscriber.message.Message) -> None:
        """Handle incoming message from Pub/Sub."""
        try:
            message_data = json.loads(message.data.decode("utf-8"))
            logger.info(f"Received ingestion job: {message_data}")

            # Call the user's callback
            callback(message_data)

            # Acknowledge the message (mark as processed)
            message.ack()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            message.nack()
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            message.nack()

    # Create streaming pull future
    logger.info(f"Subscribing to {subscription_path}")
    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=message_callback
    )

    try:
        # Block until timeout or indefinitely
        streaming_pull_future.result(timeout=timeout)
    except TimeoutError:
        logger.info("Subscription timeout reached")
    except KeyboardInterrupt:
        logger.info("Subscription interrupted by user")
    finally:
        streaming_pull_future.cancel()
        subscriber.close()
