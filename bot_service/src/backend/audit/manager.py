import json
import threading
import time
import uuid

from audit.db_models import AuditLog, AuditModelService
from common.configuration import Configuration
from common.logger import logger, tracer
from database.manager import DatabaseServiceManager
from redis.exceptions import ConnectionError, RedisError, ResponseError, TimeoutError


class AuditService:
    """Implements the audit service"""

    def __init__(
        self,
        audit_db_model_service: AuditModelService,
        database_service_manager: DatabaseServiceManager,
        config: Configuration,
    ):
        self.audit_db_model_service = audit_db_model_service
        self.database_service_manager = database_service_manager
        self.config = config

        try:
            self.r = database_service_manager.redis_db_service().redis_client
            self.redis_available = True
        except Exception as e:
            logger.warning(f"Redis not available during initialization: {e}. Falling back to direct database writes.")
            self.r = None
            self.redis_available = False

        self.stream = config.configuration().audit_log_configuration.stream
        self.group = config.configuration().audit_log_configuration.group
        self.consumer = config.configuration().audit_log_configuration.consumer
        self.batch_size = config.configuration().audit_log_configuration.batch_size
        self.block_ms = config.configuration().audit_log_configuration.block_ms
        self._stop = threading.Event()
        self.start_id = "$"  # "$" or "0"
        self.maxlen = 1_000_000
        self.min_batch_size = self.config.configuration().audit_log_configuration.min_batch_size
        self.batch_timeout = self.config.configuration().audit_log_configuration.batch_timeout
        self._pending_batch = []
        self._pending_ids = []
        self._batch_start_time = None

        # Only try to ensure group if Redis is available
        if self.redis_available:
            self._ensure_group()

    def _ensure_group(self):
        """Ensure Redis group exists, with fallback handling."""
        if not self.redis_available:
            logger.warning("Redis not available, skipping group creation")
            return

        try:
            # Create the group; MKSTREAM makes the stream if missing
            self.r.xgroup_create(name=self.stream, groupname=self.group, id=self.start_id, mkstream=True)
        except ResponseError as e:
            msg = str(e)
            if "BUSYGROUP" in msg:
                # Group already exists: OK
                return
            # Some Redis versions use different wording; if it's not BUSYGROUP, re-raise
            raise
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis connection issue during group creation: {e}. Disabling Redis.")
            self.redis_available = False
            self.r = None

    def start(self):
        """Start the consumer thread only if Redis is available."""
        if not self.redis_available:
            logger.warning("Redis not available, audit log consumer not started. Using direct database writes.")
            return

        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()
        logger.info("Audit log consumer started")

    def stop(self):
        """Stop the consumer thread and process remaining batch."""
        self._stop.set()

        # Process any remaining messages in the batch before stopping
        if self._pending_batch:
            logger.info(f"Processing final batch of {len(self._pending_batch)} messages before stopping")
            ok = self._bulk_insert(self._pending_batch)
            if ok and self.redis_available:
                try:
                    self.r.xack(self.stream, self.group, *self._pending_ids)
                except (ConnectionError, TimeoutError, RedisError) as e:
                    logger.warning(f"Failed to acknowledge messages during shutdown: {e}")

        if hasattr(self, "t"):
            self.t.join()
        logger.info("Audit log consumer stopped")

    def _run(self):
        """Main consumer loop with Redis error handling."""
        while not self._stop.is_set():
            try:
                # Check Redis availability before attempting operations
                if not self._check_redis_health():
                    time.sleep(5)  # Wait before retrying
                    continue

                # Read up to batch_size; BLOCK waits for new items
                resp = self.r.xreadgroup(self.group, self.consumer, {self.stream: ">"}, count=self.batch_size, block=self.block_ms)

                if resp:
                    # resp format: [ (stream, [ (id, {b'json': b'...'}), ... ]) ]
                    _, entries = resp[0]
                    self._process_new_messages(entries)

                # Check if we should process accumulated batch due to timeout or size
                self._check_and_process_batch()

            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis connection error in consumer: {e}. Disabling Redis and switching to direct DB writes.")
                self.redis_available = False
                self.r = None
                time.sleep(5)  # Wait before checking again
            except Exception as e:
                logger.exception(f"Error in audit log consumer loop: {e}")
                time.sleep(1)  # Brief pause before retrying

    def _check_redis_health(self) -> bool:
        """Check if Redis is available and reconnect if needed."""
        if not self.redis_available:
            try:
                # Try to reconnect
                self.r = self.database_service_manager.redis_db_service().redis_client
                # Test connection
                self.r.ping()
                self.redis_available = True
                self._ensure_group()  # Recreate group if needed
                logger.info("Redis connection restored")
                return True
            except Exception as e:
                logger.warning(f"Redis still unavailable: {e}")
                return False

        try:
            # Test existing connection
            self.r.ping()
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis health check failed: {e}")
            self.redis_available = False
            self.r = None
            return False

    def _process_new_messages(self, entries):
        """Process new messages from Redis stream and add to pending batch."""
        for msg_id, kv in entries:
            try:
                payload = json.loads(kv["json"])
                self._pending_ids.append(msg_id)
                self._pending_batch.append(
                    {
                        "name": payload.get("name"),
                        "user_id": payload["user_id"],
                        "target_id": payload["target_id"],
                        "action_type": payload["action_type"],
                        "target_type": payload["target_type"],
                        "status": payload["status"],
                        "detail": payload.get("detail"),
                        "ip_address": payload.get("ip_address"),
                        "request_id": payload.get("request_id"),
                    }
                )

                # Set batch start time if this is the first message
                if self._batch_start_time is None:
                    self._batch_start_time = time.time()

            except Exception:
                # Malformed message: move to a dead-letter stream and ACK to skip
                logger.exception("Malformed audit log message; moving to dead-letter stream")
                self._dead_letter(msg_id, kv)
                self.r.xack(self.stream, self.group, msg_id)

    def _check_and_process_batch(self):
        """Check if batch should be processed based on size or timeout."""
        if not self._pending_batch:
            return

        current_time = time.time()
        batch_age = current_time - self._batch_start_time if self._batch_start_time else 0

        should_process = len(self._pending_batch) >= self.min_batch_size or batch_age >= self.batch_timeout or len(self._pending_batch) >= self.batch_size

        if should_process:
            # logger.info(f"Processing batch: {len(self._pending_batch)} messages (age: {batch_age:.2f}s)")

            ok = self._bulk_insert(self._pending_batch)
            if ok and self.redis_available:
                try:
                    self.r.xack(self.stream, self.group, *self._pending_ids)
                    logger.info(f"Successfully processed and acknowledged {len(self._pending_batch)} audit log messages.")
                except (ConnectionError, TimeoutError, RedisError) as e:
                    logger.warning(f"Failed to acknowledge messages, but database insert succeeded: {e}")
            elif ok:
                logger.info(f"Successfully processed {len(self._pending_batch)} audit log messages (Redis unavailable)")
            else:
                logger.error(f"Failed to process batch of {len(self._pending_batch)} messages")
                if self.redis_available:
                    # Leave unacknowledged for retry only if Redis is available
                    time.sleep(0.5)

            # Reset batch regardless of success/failure
            self._pending_batch = []
            self._pending_ids = []
            self._batch_start_time = None

    def _bulk_insert(self, rows) -> bool:
        try:
            # logger.info(f"Processing {len(rows)} audit log entries for bulk insertion")

            # Directly pass the dictionaries to bulk_insert_mappings for maximum efficiency
            success = self.audit_db_model_service.create_audit_logs(rows)

            if success:
                # logger.info(f"Successfully bulk inserted {len(rows)} audit log entries")
                pass
            else:
                logger.error(f"Failed to bulk insert {len(rows)} audit log entries")

            return success
        except Exception as e:
            logger.exception(f"Failed to bulk insert audit logs due to: {e}")
            return False

    def _dead_letter(self, msg_id, kv):
        """Move malformed messages to dead letter stream with fallback handling."""
        if not self.redis_available:
            logger.warning("Cannot move message to dead letter stream - Redis unavailable")
            return

        try:
            self.r.xadd(f"{self.stream}:dead", {"orig_id": msg_id, "json": kv.get(b"json", kv.get("json", b""))})
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Failed to move message to dead letter stream: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error moving message to dead letter stream: {str(e)}")

    def log(self, **fields):
        """Log audit event with Redis fallback to direct database write."""
        # Ensure an idempotency key
        event = {"event_id": str(uuid.uuid4()), **fields}

        # Try Redis first if available
        if self.redis_available:
            try:
                # XADD with MAXLEN ~ to keep memory bounded (approximate trim)
                self.r.xadd(self.stream, {"json": json.dumps(event)}, maxlen=self.maxlen, approximate=True)
                return  # Success with Redis
            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis unavailable for logging, falling back to direct DB write: {e}")
                self.redis_available = False
                self.r = None

        # Fallback to direct database write
        try:
            audit_log_data = {
                "name": event.get("name"),
                "user_id": event.get("user_id"),
                "target_id": event.get("target_id"),
                "action_type": event.get("action_type"),
                "target_type": event.get("target_type"),
                "status": event.get("status"),
                "detail": event.get("detail"),
                "ip_address": event.get("ip_address"),
                "request_id": event.get("request_id"),
            }

            # Remove None values
            audit_log_data = {k: v for k, v in audit_log_data.items() if v is not None}

            # Direct database insert
            audit_log = AuditLog(**audit_log_data)
            success = self.audit_db_model_service.create_audit_log(audit_log)

            if success:
                logger.debug(f"Audit log written directly to database: {event.get('action_type')}")
            else:
                logger.error(f"Failed to write audit log to database: {event}")

        except Exception as e:
            logger.exception(f"Failed to log audit event both via Redis and direct DB: {e}")
            # Event is lost, but we don't want to crash the application
