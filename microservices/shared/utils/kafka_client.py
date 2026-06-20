from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from typing import Callable, Dict, Any, List, Optional
import json
import logging
from ..events.base import BaseEvent

logger = logging.getLogger(__name__)


class EventProducer:
    """Kafka event producer for publishing events"""

    def __init__(self, bootstrap_servers: List[str], topic_prefix: str = "financial_"):
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1
        )

    def publish_event(self, event: BaseEvent, topic_suffix: str = None):
        """Publish an event to Kafka"""
        try:
            topic = f"{self.topic_prefix}{topic_suffix or event.event_type.value}"
            event_data = event.to_dict()

            # Use user_id as partition key for ordering
            key = str(event.user_id) if event.user_id else event.event_id

            future = self.producer.send(
                topic,
                key=key,
                value=event_data
            )

            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            logger.info(
                f"Event published: {event.event_type.value} to {topic} "
                f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )
            return True

        except KafkaError as e:
            logger.error(f"Failed to publish event: {event.event_type.value}, Error: {str(e)}")
            raise

    def close(self):
        """Close the producer"""
        self.producer.close()


class EventConsumer:
    """Kafka event consumer for subscribing to events"""

    def __init__(
        self,
        bootstrap_servers: List[str],
        group_id: str,
        topics: List[str],
        auto_offset_reset: str = 'earliest'
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None
        )
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler function for a specific event type"""
        self.handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    def start(self):
        """Start consuming messages"""
        logger.info(f"Starting consumer for topics: {self.topics}")

        try:
            for message in self.consumer:
                try:
                    event_data = message.value
                    event_type = event_data.get('event_type')

                    logger.debug(f"Received event: {event_type} from {message.topic}")

                    # Find and execute handler
                    handler = self.handlers.get(event_type)
                    if handler:
                        handler(event_data)
                        # Commit offset after successful processing
                        self.consumer.commit()
                    else:
                        logger.warning(f"No handler registered for event type: {event_type}")
                        self.consumer.commit()  # Still commit to avoid reprocessing

                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    # Don't commit on error - message will be reprocessed

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        finally:
            self.close()

    def close(self):
        """Close the consumer"""
        self.consumer.close()
        logger.info("Consumer closed")


class EventBus:
    """Event bus for managing producers and consumers"""

    def __init__(self, bootstrap_servers: List[str], topic_prefix: str = "financial_"):
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.producer = EventProducer(bootstrap_servers, topic_prefix)
        self.consumers: List[EventConsumer] = []

    def publish(self, event: BaseEvent):
        """Publish an event"""
        return self.producer.publish_event(event)

    def subscribe(
        self,
        topics: List[str],
        group_id: str,
        handlers: Dict[str, Callable]
    ) -> EventConsumer:
        """Subscribe to topics with handlers"""
        consumer = EventConsumer(
            self.bootstrap_servers,
            group_id,
            topics
        )

        for event_type, handler in handlers.items():
            consumer.register_handler(event_type, handler)

        self.consumers.append(consumer)
        return consumer

    def close_all(self):
        """Close all producers and consumers"""
        self.producer.close()
        for consumer in self.consumers:
            consumer.close()
