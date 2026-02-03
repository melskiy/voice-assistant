from typing import Optional
from uuid import UUID
from redis.asyncio import Redis
import json
from datetime import datetime
from voice_assistant.domain.entities.session import Session
from voice_assistant.domain.entities.session import DialogState


class SessionCache:
    """Redis-based session cache using redis.asyncio"""
    
    def __init__(self, redis_client: Redis, default_ttl: int = 1800):  # 30 minutes
        self.redis = redis_client
        self.default_ttl = default_ttl
    
    async def get_session(self, session_id: UUID) -> Session | None:
        """Get session from cache"""
        key = f"session:{session_id}"
        data = await self.redis.get(key)
        
        if not data:
            return None
        
        try:
            session_dict = json.loads(data)
            return Session(
                id=UUID(session_dict['id']),
                phone_number=session_dict['phone_number'],
                state=DialogState(session_dict['state']),
                context_data=session_dict['context_data'],
                created_at=datetime.fromisoformat(session_dict['created_at']),
                last_activity=datetime.fromisoformat(session_dict['last_activity'])
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error deserializing session from cache: {e}")
            return None
    
    async def set_session(self, session: Session, ttl: int | None = None) -> bool:
        """Set session in cache"""
        key = f"session:{session.id}"
        ttl = ttl or self.default_ttl
        
        session_dict = {
            'id': str(session.id),
            'phone_number': session.phone_number,
            'state': session.state.value,
            'context_data': session.context_data,
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat()
        }
        
        try:
            await self.redis.setex(
                key, 
                ttl, 
                json.dumps(session_dict, ensure_ascii=False)
            )
            return True
        except Exception as e:
            print(f"Error setting session in cache: {e}")
            return False
    
    async def update_session_state(self, session_id: UUID, new_state: DialogState, 
                                 context_data: dict[str, any]) -> bool:
        """Update only the state and context of a session"""
        key = f"session:{session_id}"
        session = await self.get_session(session_id)
        
        if not session:
            return False
        
        session.state = new_state
        session.context_data = context_data
        session.last_activity = datetime.utcnow()
        
        return await self.set_session(session)
    
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete session from cache"""
        key = f"session:{session_id}"
        deleted_count = await self.redis.delete(key)
        return deleted_count > 0
    
    async def touch_session(self, session_id: UUID) -> bool:
        """Extend session TTL without modifying data"""
        key = f"session:{session_id}"
        ttl = await self.redis.ttl(key)
        
        if ttl > 0:
            # Only extend if session still exists
            await self.redis.expire(key, self.default_ttl)
            return True
        
        return False