"""Transform calendar events into RAG documents."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from .config import Config

logger = logging.getLogger(__name__)


class DocumentTransformer:
    """Transforms calendar events into RAG-ready documents."""
    
    def __init__(self, config: Config):
        self.config = config
        self.transformer_config = config.transformer
    
    def transform_event(self, event: Dict[str, Any], context_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Transform a calendar event into a RAG document."""
        envelope = event.get("envelope", {})
        body = event.get("body", {})
        
        # Build document ID
        doc_id = envelope.get("message_id", "")
        
        # Build content text
        content_parts = []
        
        # Event title
        title = body.get("text", "Untitled Event")
        content_parts.append(f"Event: {title}")
        content_parts.append("")
        
        # Description
        if self.transformer_config.include_description:
            description = body.get("description", "").strip()
            if description:
                # Truncate if too long
                if len(description) > self.transformer_config.max_description_length:
                    description = description[:self.transformer_config.max_description_length] + "..."
                content_parts.append(f"Description: {description}")
                content_parts.append("")
        
        # Time information
        start_time = body.get("start_time")
        end_time = body.get("end_time")
        is_all_day = body.get("all_day", False)
        
        if start_time:
            if is_all_day:
                # Extract just the date
                date_part = start_time.split("T")[0]
                content_parts.append(f"Date: {date_part} (All Day)")
            else:
                content_parts.append(f"Starts: {start_time}")
                if end_time:
                    content_parts.append(f"Ends: {end_time}")
        
        # Location
        if self.transformer_config.include_location:
            location = body.get("location", "").strip()
            if location:
                content_parts.append(f"Location: {location}")
        
        # Attendees/Participants
        if self.transformer_config.include_attendees:
            participants = envelope.get("participants", [])
            if participants:
                attendee_names = []
                for p in participants:
                    name = p.get("display_name") or p.get("email", "")
                    if name:
                        attendee_names.append(name)
                
                if attendee_names:
                    content_parts.append(f"Participants: {', '.join(attendee_names)}")
        
        # Calendar context
        context_label = envelope.get("context_label", "")
        if context_label:
            content_parts.append(f"Calendar: {context_label}")
        
        # Status and recurring info
        status = body.get("status", "confirmed")
        if status != "confirmed":
            content_parts.append(f"Status: {status}")
        
        if body.get("recurring", False):
            content_parts.append("(Recurring Event)")
        
        # Combine content
        content = "\n".join(content_parts)
        
        # Build metadata
        metadata = {
            "source_channel": envelope.get("source_channel", "calendar"),
            "source_instance": envelope.get("source_instance", ""),
            "calendar_id": envelope.get("context_id", ""),
            "calendar_name": context_label,
            "event_id": envelope.get("remote_id", ""),
            "event_type": "calendar_event",
            "start_time": start_time,
            "end_time": end_time,
            "is_all_day": is_all_day,
            "status": status,
            "recurring": body.get("recurring", False),
        }
        
        # Add location to metadata if available
        if self.transformer_config.include_location:
            location = body.get("location", "").strip()
            if location:
                metadata["location"] = location
        
        # Add organizer/creator to metadata
        sender = envelope.get("sender", {})
        if sender:
            metadata["organizer"] = sender.get("email", sender.get("id", ""))
            metadata["organizer_name"] = sender.get("display_name", "")
        
        # Add attendees to metadata
        if self.transformer_config.include_attendees:
            participants = envelope.get("participants", [])
            if participants:
                attendee_emails = [p.get("email", "") for p in participants if p.get("email")]
                if attendee_emails:
                    metadata["attendees"] = attendee_emails
        
        # Add timestamp for indexing tracking
        metadata["indexed_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Parse timestamp from envelope for date-based filtering
        ts_str = envelope.get("ts", "")
        if ts_str:
            metadata["event_timestamp"] = ts_str
        
        return {
            "id": doc_id,
            "content": content,
            "metadata": metadata,
        }
    
    def batch_transform(
        self,
        events: List[Dict[str, Any]],
        context_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Transform a batch of events into RAG documents."""
        documents = []
        
        for event in events:
            try:
                doc = self.transform_event(event, context_metadata)
                documents.append(doc)
            except Exception as e:
                logger.warning(f"Failed to transform event {event.get('envelope', {}).get('message_id', 'unknown')}: {e}")
                continue
        
        return documents

