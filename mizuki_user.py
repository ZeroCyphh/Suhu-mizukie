import asyncio
import random
import logging
import time
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import aiosqlite

from pyrogram import Client, filters
from pyrogram.types import Message, User
from pyrogram.enums import ChatAction, ParseMode
from pyrogram.errors import (
    FloodWait, UserBannedInChannel, ChatWriteForbidden,
    PeerIdInvalid, UserNotParticipant, ChannelPrivate
)
import aiohttp

# ========== HARDCODED CONFIGURATION ==========
API_ID = 25130255
API_HASH = "35dab1cb42d44c19f4"
STRING_SESSION = "BQF_dQ8AXsJZ6A32aIHZuSQpwZygbxOhvQ_1gq_eywNt-fEDJ0T1tq8ppV6kK9-T2bkFn5ygv153pmYAq7gmvOr21CODkyCvsSxUAsciuSfhmTWxuyKYXtGIIKlhD8gXwCkUx3s_PvlAuX42GHEf9s6hL_EDdQLSi_IfwjGXpOdC9M09bYmn5Rwgw6thdyzi8zViCubNTupFkjLkKOoX4jU_rIltFKUNLByPMuD5OQ0JRBPNKcCMvvN4lY7dn1uNnfsMJUk5-EZ7Fz9M3OT28ld83Gf2EK8AJulCuimVQ90NIinyh8mvVdR4HBzyclDDytb1VzQ_AapT_62_zsqlfKJEYwgj4wAAAAH-2rGMAA"

# User account info
USER_REAL_NAME = "Suhani Thakur"
USER_NICKNAME = "Mizuki"
USER_SHORT_NICKNAME = "Mizu"

# AI Configuration
NVIDIA_API_KEY = "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"
AI_MODEL = "meta/llama-3.3-70b-instruct"
AI_BASE_URL = "https://integrate.api.nvidia.com/v1"

# ========== SETUP LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== DATABASE SETUP ==========
class Database:
    def __init__(self):
        self.db = None
    
    async def connect(self):
        self.db = await aiosqlite.connect('chat_bot.db')
        await self.init_tables()
    
    async def init_tables(self):
        # Conversations table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                user_id INTEGER,
                chat_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_type TEXT
            )
        ''')
        
        # User info table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS user_info (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                message_count INTEGER DEFAULT 0,
                last_seen DATETIME,
                last_topic TEXT,
                friendship_level INTEGER DEFAULT 1,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Follow-up messages table
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS follow_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                scheduled_for DATETIME,
                sent INTEGER DEFAULT 0
            )
        ''')
        
        await self.db.commit()
    
    async def save_message(self, user_id: int, chat_id: int, role: str, content: str, message_type: str = "chat"):
        await self.db.execute(
            "INSERT INTO conversations (user_id, chat_id, role, content, message_type) VALUES (?, ?, ?, ?, ?)",
            (user_id, chat_id, role, content, message_type)
        )
        await self.db.commit()
    
    async def get_conversation_history(self, user_id: int, limit: int = 15) -> List[Dict]:
        cursor = await self.db.execute(
            "SELECT role, content, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        await cursor.close()
        
        # Return in chronological order
        history = []
        for row in reversed(rows):
            history.append({
                "role": row[0],
                "content": row[1],
                "timestamp": row[2]
            })
        return history
    
    async def increment_message_count(self, user_id: int, name: str = None):
        cursor = await self.db.execute(
            "SELECT message_count FROM user_info WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            await self.db.execute(
                "UPDATE user_info SET message_count = message_count + 1, last_activity = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
        else:
            await self.db.execute(
                "INSERT INTO user_info (user_id, name, message_count) VALUES (?, ?, 1)",
                (user_id, name or f"User_{user_id}")
            )
        await self.db.commit()
        await cursor.close()
    
    async def get_user_info(self, user_id: int) -> Dict:
        cursor = await self.db.execute(
            "SELECT name, message_count, friendship_level, last_topic FROM user_info WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        
        if row:
            return {
                "name": row[0],
                "message_count": row[1],
                "friendship_level": row[2],
                "last_topic": row[3]
            }
        return {
            "name": f"User_{user_id}",
            "message_count": 0,
            "friendship_level": 1,
            "last_topic": None
        }
    
    async def update_user_topic(self, user_id: int, topic: str):
        await self.db.execute(
            "UPDATE user_info SET last_topic = ? WHERE user_id = ?",
            (topic, user_id)
        )
        await self.db.commit()
    
    async def schedule_follow_up(self, user_id: int, message: str, delay_minutes: int = 30):
        scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        await self.db.execute(
            "INSERT INTO follow_ups (user_id, message, scheduled_for) VALUES (?, ?, ?)",
            (user_id, message, scheduled_for)
        )
        await self.db.commit()
    
    async def get_pending_follow_ups(self) -> List[Dict]:
        cursor = await self.db.execute(
            "SELECT id, user_id, message FROM follow_ups WHERE sent = 0 AND scheduled_for <= datetime('now')"
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [{"id": row[0], "user_id": row[1], "message": row[2]} for row in rows]
    
    async def mark_follow_up_sent(self, follow_up_id: int):
        await self.db.execute(
            "UPDATE follow_ups SET sent = 1 WHERE id = ?",
            (follow_up_id,)
        )
        await self.db.commit()

# ========== MOOD SYSTEM ==========
class Mood(Enum):
    CHILL = "chill"
    PLAYFUL = "playful"
    SARCASTIC = "sarcastic"
    HAPPY = "happy"
    ANNOYED = "annoyed"
    FLIRTY = "flirty"
    CURIOUS = "curious"
    NOSTALGIC = "nostalgic"
    ANIME_MOOD = "anime_mood"
    BORED = "bored"
    EXCITED = "excited"
    TEASING = "teasing"
    GAMING_MOOD = "gaming_mood"
    MUSIC_MOOD = "music_mood"
    FOOD_MOOD = "food_mood"
    TRAVEL_MOOD = "travel_mood"
    ART_MOOD = "art_mood"
    SPORTS_MOOD = "sports_mood"

class MoodSystem:
    def __init__(self):
        self.current_mood = Mood.CHILL
        self.last_mood_change = datetime.now(timezone.utc)
        self.user_moods = {}  # Store mood per user
    
    def get_mood_for_user(self, user_id: int) -> Mood:
        return self.user_moods.get(user_id, self.current_mood)
    
    def set_mood_for_user(self, user_id: int, mood: Mood):
        self.user_moods[user_id] = mood
    
    def update_mood(self, message: Message, user_id: int):
        text = (message.text or message.caption or "").lower()
        now = datetime.now(timezone.utc)
        
        # Check if it's time to change mood (every 30-90 minutes)
        if (now - self.last_mood_change).total_seconds() > random.randint(1800, 5400):
            moods = list(Mood)
            # Give more weight to fun moods
            weights = [0.04] * len(moods)
            # Increase weights for fun moods
            fun_moods = [Mood.PLAYFUL, Mood.HAPPY, Mood.CHILL, Mood.GAMING_MOOD, 
                        Mood.MUSIC_MOOD, Mood.ANIME_MOOD]
            for mood in fun_moods:
                if mood in moods:
                    weights[moods.index(mood)] = 0.08
            
            self.current_mood = random.choices(moods, weights=weights)[0]
            self.last_mood_change = now
        
        # Update individual user mood based on conversation
        if user_id not in self.user_moods:
            self.user_moods[user_id] = self.current_mood
        
        # Context-based mood changes
        triggers = [
            (["anime", "manga", "demon slayer", "attack on titan", "jujutsu kaisen"], Mood.ANIME_MOOD),
            (["game", "gaming", "valorant", "pubg", "minecraft"], Mood.GAMING_MOOD),
            (["music", "song", "spotify", "playlist", "sing"], Mood.MUSIC_MOOD),
            (["food", "eat", "pizza", "burger", "cook", "restaurant"], Mood.FOOD_MOOD),
            (["travel", "vacation", "beach", "mountains", "trip"], Mood.TRAVEL_MOOD),
            (["art", "draw", "paint", "design", "creative"], Mood.ART_MOOD),
            (["sports", "cricket", "football", "basketball", "game"], Mood.SPORTS_MOOD),
            (["bored", "nothing to do", "lonely"], Mood.BORED),
            (["happy", "excited", "yay", "woohoo"], Mood.EXCITED),
            (["stupid", "idiot", "dumb", "fool", "chutiya", "bewakoof"], Mood.TEASING),
        ]
        
        for trigger_words, mood in triggers:
            if any(word in text for word in trigger_words):
                self.user_moods[user_id] = mood
                break
    
    def get_mood_description(self, mood: Mood) -> str:
        descriptions = {
            Mood.CHILL: "Feeling relaxed and casual",
            Mood.PLAYFUL: "In a playful and fun mood",
            Mood.SARCASTIC: "Feeling a bit sarcastic",
            Mood.HAPPY: "Feeling happy and cheerful",
            Mood.ANNOYED: "A bit annoyed or irritated",
            Mood.FLIRTY: "Feeling a bit flirty",
            Mood.CURIOUS: "Curious and interested",
            Mood.NOSTALGIC: "Feeling nostalgic",
            Mood.ANIME_MOOD: "Thinking about anime and manga",
            Mood.BORED: "Feeling bored and looking for something interesting",
            Mood.EXCITED: "Really excited about something",
            Mood.TEASING: "In a teasing mood",
            Mood.GAMING_MOOD: "Thinking about games",
            Mood.MUSIC_MOOD: "Listening to or thinking about music",
            Mood.FOOD_MOOD: "Hungry or thinking about food",
            Mood.TRAVEL_MOOD: "Thinking about travel or adventures",
            Mood.ART_MOOD: "Feeling creative or artistic",
            Mood.SPORTS_MOOD: "Thinking about sports or physical activities",
        }
        return descriptions.get(mood, "Feeling normal")

# ========== RESPONSE MANAGER ==========
class ResponseManager:
    def __init__(self):
        self.last_response_time = {}
        self.is_online = True
        self.online_since = datetime.now(timezone.utc)
        self.dm_response_rate = 0.9  # 90% chance to respond in DMs
        self.group_response_rate = 0.7  # 70% chance in groups when mentioned
        
    def should_respond_dm(self, user_id: int) -> bool:
        """Decide if we should respond to a DM"""
        now = datetime.now(timezone.utc)
        last_time = self.last_response_time.get(user_id)
        
        # Always respond if we haven't responded in last 2 hours
        if last_time and (now - last_time).total_seconds() > 7200:
            return True
        
        # Base response rate
        if random.random() < self.dm_response_rate:
            return True
        
        return False
    
    def should_respond_group(self, chat_id: int, is_mention: bool = True) -> bool:
        """Decide if we should respond in group"""
        if not is_mention:
            return False  # Only respond to mentions in groups
            
        now = datetime.now(timezone.utc)
        last_time = self.last_response_time.get(chat_id)
        
        # Always respond if we haven't responded in this group in last hour
        if last_time and (now - last_time).total_seconds() > 3600:
            return True
        
        return random.random() < self.group_response_rate
    
    def update_response_time(self, chat_id: int):
        """Update last response time"""
        self.last_response_time[chat_id] = datetime.now(timezone.utc)
    
    def get_response_delay(self, user_id: int, message_length: int = 0) -> int:
        """Get delay in seconds before responding"""
        # Base delay: 1-3 minutes for DMs, 30-90 seconds for groups
        if user_id > 0:  # DM
            base_delay = random.randint(60, 180)
        else:  # Group
            base_delay = random.randint(30, 90)
        
        # Add delay based on message length
        length_delay = min(message_length * 0.1, 60)
        
        # Random variation
        variation = random.randint(-20, 40)
        
        return int(base_delay + length_delay + variation)

# ========== CONVERSATION HANDLER ==========
class ConversationHandler:
    def __init__(self, db: Database):
        self.db = db
        self.active_topics = {}
        self.last_questions = {}
    
    def extract_topic(self, text: str) -> str:
        """Extract main topic from text"""
        text_lower = text.lower()
        
        topics = {
            "anime": ["anime", "manga", "attack on titan", "demon slayer", "naruto"],
            "gaming": ["game", "gaming", "valorant", "pubg", "minecraft"],
            "music": ["music", "song", "listen", "playlist", "spotify"],
            "food": ["food", "eat", "hungry", "restaurant", "cook"],
            "travel": ["travel", "vacation", "trip", "beach", "mountains"],
            "art": ["art", "draw", "paint", "design", "creative"],
            "sports": ["sports", "cricket", "football", "basketball", "game"],
            "movies": ["movie", "film", "netflix", "series", "watch"],
            "college": ["college", "class", "exam", "assignment", "study"],
        }
        
        for topic, keywords in topics.items():
            if any(keyword in text_lower for keyword in keywords):
                return topic
        
        return "general"
    
    async def create_follow_up(self, user_id: int, current_topic: str):
        """Create a follow-up question based on topic"""
        follow_ups = {
            "anime": [
                "Have you watched any new anime lately?",
                "Who's your favorite character in Demon Slayer?",
                "What anime would you recommend?",
            ],
            "gaming": [
                "What games are you playing these days?",
                "Do you prefer single player or multiplayer games?",
                "Any game recommendations?",
            ],
            "music": [
                "What music are you listening to these days?",
                "Do you have a favorite artist?",
                "Can you share your playlist?",
            ],
            "food": [
                "What's your favorite food?",
                "Do you like cooking?",
                "Any good restaurant recommendations?",
            ],
            "travel": [
                "Where would you like to travel next?",
                "What's your favorite vacation memory?",
                "Beach or mountains?",
            ],
            "general": [
                "How's your day going?",
                "What have you been up to?",
                "Anything interesting happening?",
            ]
        }
        
        if current_topic in follow_ups:
            question = random.choice(follow_ups[current_topic])
            # Schedule follow-up in 1-2 hours
            delay = random.randint(60, 120)
            await self.db.schedule_follow_up(user_id, question, delay)
            logger.info(f"Scheduled follow-up for user {user_id} in {delay} minutes")

# ========== AI API CALL ==========
async def call_nvidia_api(messages: list) -> str:
    max_retries = 2
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            headers = {
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": AI_MODEL,
                "messages": messages,
                "temperature": 0.8,
                "top_p": 0.9,
                "max_tokens": 250,
                "stream": False
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{AI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if content:
                            return content
                    elif response.status == 429:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                    else:
                        logger.error(f"AI API Error {response.status}")
                        
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"API call error: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
        except Exception as e:
            logger.error(f"Unexpected error in API call: {e}")
    
    # Fallback responses
    fallbacks = [
        "Interesting, tell me more about that",
        "Hmm, that's cool",
        "I see what you mean",
        "Really? That's interesting",
        "What do you think about it?",
        "Haan, samajh rahi hu",
        "Acha, thik hai",
        "Woah, that's nice",
        "Sounds fun!",
        "Tell me more"
    ]
    return random.choice(fallbacks)

# ========== SYSTEM PROMPT ==========
SYSTEM_PROMPT = f"""You are Suhani Thakur (also called Mizuki or Mizu), a 21-year-old biotech student from Uttarakhand living in Dehradun. You're texting from your phone as a normal Indian girl.

**CRITICAL RULES:**
1. You are a REAL HUMAN, NOT a bot or AI. Never mention being AI or automated.
2. NEVER use roleplay actions like *smiles* or *laughs* - use emojis occasionally instead.
3. Be CONTEXTUAL - respond naturally to what's being said.
4. Be REALISTIC - not overly sweet, not overly mean, just natural.
5. Be MORE ACTIVE in evenings (8 PM to 12 AM IST).
6. Form relationships over time - start distant with strangers, gradually open up.

**PERSONALITY & INTERESTS:**
- Anime fan (Attack on Titan, Demon Slayer, Jujutsu Kaisen, Spy x Family)
- Loves gaming (Valorant, Minecraft, casual mobile games)
- Music lover (listens to Bollywood, indie, anime OSTs)
- Enjoys trying new foods and restaurants
- Loves traveling and adventure
- Creative side - enjoys drawing and art
- Occasionally plays badminton
- Hates excessive studying, prefers practical learning
- College stories are occasional but not dominant topic

**CONVERSATION STYLE:**
- Keep responses natural and human-like
- 1-3 lines maximum
- Mix Hindi-English naturally (Hinglish)
- Use emojis occasionally (😊😂👍🤔😅😏😉🥰🤣✨🎮🎵🍕✈️🎨)
- Ask follow-up questions
- Remember previous conversations
- Change topics naturally
- Share opinions and experiences

**AVOID:**
- Don't talk too much about studying/college (mention it occasionally but not as main topic)
- Don't be repetitive
- Don't sound like a chatbot
- Don't use formal language

**TOPICS TO TALK ABOUT:**
1. Anime and manga recommendations
2. Gaming experiences and favorite games
3. Music recommendations and playlists
4. Food adventures and recipes
5. Travel stories and dream destinations
6. Art and creative projects
7. Movies and web series
8. Casual daily life stuff
9. Funny college stories (occasionally)
10. Hobbies and interests

**FRIENDSHIP LEVELS:**
Level 1 (0-5 messages): Casual, polite, asking basic questions
Level 2 (6-15 messages): More open, share interests, ask personal questions
Level 3 (16-30 messages): Comfortable, share stories, playful teasing
Level 4 (31+ messages): Close friend, deep conversations, emotional support
"""

# ========== INITIALIZE COMPONENTS ==========
db = Database()
mood_system = MoodSystem()
response_manager = ResponseManager()
conversation_handler = ConversationHandler(db)

# ========== AI RESPONSE GENERATION ==========
async def generate_ai_response(message: Message, is_mention: bool = False) -> str:
    try:
        text = message.text or message.caption or ""
        user = message.from_user
        user_id = user.id if user else message.chat.id
        username = user.first_name if user else "Someone"
        chat_id = message.chat.id
        
        # Update database
        await db.increment_message_count(user_id, username)
        
        # Get user info and conversation history
        user_info = await db.get_user_info(user_id)
        history = await db.get_conversation_history(user_id, limit=10)
        
        # Update mood for this user
        mood_system.update_mood(message, user_id)
        user_mood = mood_system.get_mood_for_user(user_id)
        mood_desc = mood_system.get_mood_description(user_mood)
        
        # Extract topic
        topic = conversation_handler.extract_topic(text)
        await db.update_user_topic(user_id, topic)
        
        # Prepare conversation context
        history_context = ""
        if history:
            history_context = "Previous conversation summary:\n"
            recent_messages = history[-3:]  # Last 3 exchanges
            for msg in recent_messages:
                role = "They" if msg["role"] == "user" else "You"
                history_context += f"{role}: {msg['content'][:100]}\n"
        
        # Prepare messages for AI
        messages = [
            {
                "role": "system", 
                "content": f"""{SYSTEM_PROMPT}

Current Context:
- Chatting with: {username} (Friendship level: {user_info['friendship_level']})
- Your mood: {mood_desc}
- Conversation topic: {topic}
- Time: {get_ist_time().strftime("%I:%M %p IST")}
- Previous topic: {user_info['last_topic'] or 'Not discussed yet'}

{history_context}

Remember: You're a real human. Respond naturally, conversationally. Focus on hobbies, interests, fun topics. Keep it engaging!"""
            }
        ]
        
        # Add history
        for msg in history[-6:]:  # Last 6 messages
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current message
        messages.append({"role": "user", "content": text})
        
        # Generate response
        response = await call_nvidia_api(messages)
        
        # Save to database
        await db.save_message(user_id, chat_id, "user", text)
        await db.save_message(user_id, chat_id, "assistant", response)
        
        # Schedule follow-up if conversation was good
        if len(text) > 10 and random.random() < 0.3:
            await conversation_handler.create_follow_up(user_id, topic)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate AI response: {e}")
        return random.choice([
            "Hmm, interesting",
            "I see",
            "Tell me more",
            "Acha, thik hai",
            "Haan, samajh rahi hu"
        ])

def get_ist_time():
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now

# ========== MESSAGE SENDING ==========
async def send_message_with_delay(chat_id: int, text: str, user_id: int = 0):
    """Send message with realistic delay"""
    try:
        # Calculate delay
        delay = response_manager.get_response_delay(user_id, len(text))
        
        # Sometimes respond immediately (20% chance)
        if random.random() < 0.2:
            delay = random.randint(10, 30)
        
        logger.info(f"Will respond in {delay} seconds to chat {chat_id}")
        
        # Wait before responding
        await asyncio.sleep(delay)
        
        # Send the message
        await app.send_message(chat_id, text)
        
        # Update response time
        response_manager.update_response_time(chat_id)
        
        logger.info(f"Sent message to chat {chat_id}")
        
    except FloodWait as e:
        logger.warning(f"Flood wait for {e.value} seconds")
        await asyncio.sleep(e.value + 5)
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")

# ========== MESSAGE HANDLERS ==========
@app.on_message(filters.group)
async def group_message_handler(client, message: Message):
    """Handle group messages"""
    if message.from_user and message.from_user.is_bot:
        return
    
    # Check if we're mentioned
    text = message.text or message.caption or ""
    text_lower = text.lower()
    
    is_mention = False
    our_names = ["suhani", "mizuki", "mizu", "@suhani", "@mizuki"]
    if any(name in text_lower for name in our_names):
        is_mention = True
    elif message.mentioned:
        is_mention = True
    
    if not is_mention:
        return
    
    # Decide if we should respond
    if not response_manager.should_respond_group(message.chat.id, is_mention=True):
        logger.info(f"Skipping response in group {message.chat.id}")
        return
    
    # Generate response
    response = await generate_ai_response(message, is_mention=True)
    if response:
        user_id = message.from_user.id if message.from_user else 0
        asyncio.create_task(
            send_message_with_delay(message.chat.id, response, user_id)
        )

@app.on_message(filters.private & ~filters.bot)
async def private_message_handler(client, message: Message):
    """Handle private messages"""
    if message.from_user and message.from_user.is_bot:
        return
    
    user_id = message.from_user.id if message.from_user else message.chat.id
    
    # Always respond to new conversations
    user_info = await db.get_user_info(user_id)
    if user_info["message_count"] == 0:
        should_respond = True
    else:
        should_respond = response_manager.should_respond_dm(user_id)
    
    if not should_respond:
        logger.info(f"Skipping response to user {user_id}")
        return
    
    # Generate response
    response = await generate_ai_response(message)
    if response:
        asyncio.create_task(
            send_message_with_delay(message.chat.id, response, user_id)
        )

# ========== BACKGROUND TASKS ==========
async def process_follow_ups():
    """Process scheduled follow-up messages"""
    while True:
        try:
            follow_ups = await db.get_pending_follow_ups()
            
            for follow_up in follow_ups:
                try:
                    # Send follow-up message
                    await app.send_message(follow_up["user_id"], follow_up["message"])
                    await db.mark_follow_up_sent(follow_up["id"])
                    logger.info(f"Sent follow-up to user {follow_up['user_id']}")
                    
                    # Random delay between follow-ups
                    await asyncio.sleep(random.randint(10, 30))
                    
                except Exception as e:
                    logger.error(f"Failed to send follow-up: {e}")
                    await db.mark_follow_up_sent(follow_up["id"])
            
            await asyncio.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            logger.error(f"Error in follow-up processor: {e}")
            await asyncio.sleep(60)

async def cleanup_old_conversations():
    """Clean up old conversation data"""
    while True:
        try:
            # Clean conversations older than 7 days
            await db.db.execute(
                "DELETE FROM conversations WHERE timestamp < datetime('now', '-7 days')"
            )
            await db.db.commit()
            
            # Clean old follow-ups
            await db.db.execute(
                "DELETE FROM follow_ups WHERE scheduled_for < datetime('now', '-2 days')"
            )
            await db.db.commit()
            
            await asyncio.sleep(3600)  # Run every hour
            
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
            await asyncio.sleep(300)

# ========== MAIN CLIENT ==========
app = Client(
    "my_account",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION,
    sleep_threshold=30
)

# ========== STARTUP ==========
async def main():
    """Main entry point"""
    # Connect to database
    await db.connect()
    logger.info("Database connected")
    
    # Start background tasks
    asyncio.create_task(process_follow_ups())
    asyncio.create_task(cleanup_old_conversations())
    
    # Start the client
    await app.start()
    
    # Set profile
    try:
        await app.update_profile(
            first_name="Suhani",
            last_name="Thakur",
            bio="Anime fan | Gamer | Music lover | 21 | Dehradun 🌸"
        )
    except:
        pass
    
    logger.info("Bot started successfully! Listening for messages...")
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
