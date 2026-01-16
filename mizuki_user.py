import asyncio
import random
import logging
import time
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import sqlite3
import threading

from pyrogram import Client, filters
from pyrogram.types import Message, User
from pyrogram.enums import ChatAction
from pyrogram.errors import FloodWait
import aiohttp

# ========== HARDCODED CONFIGURATION ==========
API_ID = 25130255
API_HASH = "35dab1cb42d44c19f4"
STRING_SESSION = "BQF_dQ8AXsJZ6A32aIHZuSQpwZygbxOhvQ_1gq_eywNt-fEDJ0T1tq8ppV6kK9-T2bkFn5ygv153pmYAq7gmvOr21CODkyCvsSxUAsciuSfhmTWxuyKYXtGIIKlhD8gXwCkUx3s_PvlAuX42GHEf9s6hL_EDdQLSi_IfwjGXpOdC9M09bYmn5Rwgw6thdyzi8zViCubNTupFkjLkKOoX4jU_rIltFKUNLByPMuD5OQ0JRBPNKcCMvvN4lY7dn1uNnfsMJUk5-EZ7Fz9M3OT28ld83Gf2EK8AJulCuimVQ90NIinyh8mvVdR4HBzyclDDytb1VzQ_AapT_62_zsqlfKJEYwgj4wAAAAH-2rGMAA"

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

# ========== NAME & BIO ROTATION ==========
NAME_VARIANTS = [
    ("Suhani", "Thakur"),
    ("𝐒𝐮𝐡𝐚𝐧𝐢", "𝐓𝐡𝐚𝐤𝐮𝐫"),
    ("ꜱᴜʜᴀɴɪ", "ᴛʜᴀᴋᴜʀ"),
    ("S͎u͎h͎a͎n͎i͎", "T͎h͎a͎k͎u͎r͎"),
    ("Ṩȗĥȃƞĩ", "Ŧĥȃƙȗř"),
    ("Mizuki", ""),
    ("ᴍɪᴢᴜᴋɪ", ""),
    ("𝕄𝕚𝕫𝕦𝕜𝕚", ""),
    ("M̶i̶z̶u̶k̶i̶", ""),
    ("S U H A N I", ""),
    ("ˢᵘʰᵃⁿⁱ", "ᵀʰᵃᵏᵘʳ"),
]

BIO_VARIANTS = [
    "🌸 21 | Anime Enthusiast | Music Lover",
    "✨ Krishna sada shayate | राधे राधे",
    "🎮 Gamer Girl | Valorant & BGMI",
    "🎵 Bollywood + Anime OSTs = Life",
    "🍕 Foodie | Chai ☕ Lover",
    "✈️ Travel Diaries | Mountains > Beaches",
    "🎨 Creative Soul | Digital Art",
    "📸 Photography | Aesthetic Vibes",
    "💫 Har har Mahadev | Jai Shree Ram",
    "🌟 सबका अपना अपना स्टार है",
    "🦋 Butterfly energy | Good vibes only",
    "☁️ Lost in clouds & thoughts",
    "🎭 Drama Queen (sometimes)",
    "💌 Soft heart, strong mind",
    "🌙 Night owl | Coffee addict",
    "🫶 Spread love, not hate",
    "💖 It's the girl, hi!",
    "🌸 जहां सोच वहां राह",
    "✨ तेरी मेरी कहानी, मीठी मीठी बातें",
    "💫 जिंदगी की रफ्तार, दोस्तों का प्यार",
]

# ========== TRENDING TOPICS ==========
TRENDING_TOPICS = [
    "Jujutsu Kaisen new season",
    "Chainsaw Man Part 2 theories",
    "Demon Slayer Hashira Training arc",
    "Spy x Family Season 2",
    "Valorant new agent",
    "BGMI unban and updates",
    "GTA 6 release rumors",
    "Punjabi music hits 2024",
    "Anuv Jain concert tour",
    "AP Dhillon latest album",
    "Taylor Swift Eras Tour India",
    "Salaar 2 announcement",
    "Animal Park teaser",
    "Mirzapur 3 release date",
    "Instagram Reels trends",
    "Threads app vs Twitter",
    "Sigma male edits",
    "Indian meme pages",
    "Coquette aesthetic fashion",
    "Y2K fashion comeback",
    "Skincare routines viral",
    "iPhone 16 leaks",
    "Android vs iOS debates",
    "AI tools for students",
    "Custom PC building",
    "Fest season college fests",
    "Internship struggles",
    "Placement season anxiety",
    "Hostel life stories",
    "College canteen food reviews",
    "Situationships gen-z style",
    "Dating app experiences",
    "Long distance relationship tips",
    "Bollywood movie reviews",
    "Web series recommendations",
    "Music festival experiences",
    "Road trips with friends",
    "Food vlogging trends",
    "Gym transformation journeys",
    "Mental health awareness",
]

# ========== SIMPLE DATABASE USING DICTIONARIES ==========
class SimpleDatabase:
    def __init__(self):
        self.conversations = {}
        self.user_relationships = {}
        self.active_conversations = {}
        
    def save_message(self, user_id: int, chat_id: int, role: str, content: str, is_group: bool = False):
        if chat_id not in self.conversations:
            self.conversations[chat_id] = []
        
        self.conversations[chat_id].append({
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
            "is_group": is_group
        })
        
        # Keep only last 50 messages per chat
        if len(self.conversations[chat_id]) > 50:
            self.conversations[chat_id] = self.conversations[chat_id][-50:]
    
    def get_conversation_history(self, chat_id: int, limit: int = 10) -> List[Dict]:
        if chat_id not in self.conversations:
            return []
        
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.conversations[chat_id][-limit:]
        ]
    
    def update_user_relationship(self, user_id: int, chat_id: int):
        if user_id not in self.user_relationships:
            self.user_relationships[user_id] = {
                "chat_id": chat_id,
                "message_count": 0,
                "friendship_level": 1,
                "last_interaction": datetime.now(timezone.utc)
            }
        
        self.user_relationships[user_id]["message_count"] += 1
        self.user_relationships[user_id]["last_interaction"] = datetime.now(timezone.utc)
        
        # Update friendship level
        count = self.user_relationships[user_id]["message_count"]
        if count < 5:
            level = 1
        elif count < 15:
            level = 2
        elif count < 30:
            level = 3
        elif count < 50:
            level = 4
        else:
            level = 5
        
        self.user_relationships[user_id]["friendship_level"] = level
    
    def get_user_info(self, user_id: int) -> Dict:
        if user_id in self.user_relationships:
            info = self.user_relationships[user_id]
            return {
                "message_count": info["message_count"],
                "friendship_level": info["friendship_level"]
            }
        return {"message_count": 0, "friendship_level": 1}
    
    def update_active_conversation(self, chat_id: int, user_id: int):
        self.active_conversations[chat_id] = {
            "user_id": user_id,
            "last_active": datetime.now(timezone.utc),
            "is_online": True,
            "response_count": self.active_conversations.get(chat_id, {}).get("response_count", 0) + 1
        }
    
    def get_active_conversations(self) -> List[int]:
        now = datetime.now(timezone.utc)
        active = []
        
        for chat_id, info in self.active_conversations.items():
            if info.get("is_online", False):
                last_active = info.get("last_active")
                if last_active and (now - last_active).total_seconds() < 7200:  # 2 hours
                    active.append(chat_id)
        
        return active
    
    def end_conversation(self, chat_id: int):
        if chat_id in self.active_conversations:
            self.active_conversations[chat_id]["is_online"] = False

# ========== CONVERSATION MANAGER ==========
class ConversationManager:
    def __init__(self):
        self.mentioned_users = {}  # chat_id -> set of user_ids who mentioned us
        self.last_response_time = {}
        self.conversation_starter_questions = [
            "Hey! What's up?",
            "How's your day going?",
            "Tell me something about yourself!",
            "What do you like to do for fun?",
            "Any cool plans for the weekend?",
            "What kind of music are you into?",
            "Do you watch anime or any series?",
            "Tell me about your hobbies!",
            "What's your favorite thing to do when you're free?",
            "Are you into gaming by any chance?",
        ]
    
    def should_respond(self, message: Message, is_mention: bool = False) -> bool:
        """Decide if we should respond to this message"""
        chat_id = message.chat.id
        user_id = message.from_user.id if message.from_user else 0
        text = (message.text or message.caption or "").lower()
        
        # Always respond to first mention in groups
        if is_mention:
            if chat_id not in self.mentioned_users:
                self.mentioned_users[chat_id] = set()
            self.mentioned_users[chat_id].add(user_id)
            return True
        
        # Check if user has mentioned us before in this chat
        if chat_id in self.mentioned_users and user_id in self.mentioned_users[chat_id]:
            # High probability to respond if they're talking to us
            our_names = ["suhani", "mizuki", "mizu", "you"]
            if any(name in text for name in our_names):
                return random.random() < 0.9
            # If replying to our message
            if message.reply_to_message and message.reply_to_message.from_user:
                if message.reply_to_message.from_user.is_self:
                    return True
        
        # For DMs - always respond (95% chance)
        if message.chat.type == "private":
            return random.random() < 0.95
        
        return False
    
    def get_response_delay(self, chat_id: int, is_new_conversation: bool = False) -> float:
        """Calculate response delay"""
        # If conversation is ongoing, respond quickly (1-10 seconds)
        current_time = time.time()
        last_time = self.last_response_time.get(chat_id, 0)
        
        # If we responded recently, respond quickly to keep conversation flowing
        if current_time - last_time < 300:  # 5 minutes
            return random.uniform(1, 10)
        
        # For new conversations, sometimes immediate, sometimes short delay
        if is_new_conversation:
            if random.random() < 0.6:  # 60% chance for quick response
                return random.uniform(2, 15)
            else:
                return random.uniform(30, 180)  # 30 seconds to 3 minutes
        
        # Default delay
        return random.uniform(5, 60)
    
    def update_response_time(self, chat_id: int):
        self.last_response_time[chat_id] = time.time()
    
    def get_conversation_starter(self) -> str:
        """Get a question to start conversation"""
        return random.choice(self.conversation_starter_questions)
    
    def get_trending_topic(self) -> str:
        """Get a random trending topic"""
        return random.choice(TRENDING_TOPICS)

# ========== GIRL CHAT STYLES ==========
class GirlChatStyle:
    @staticmethod
    def get_friendly_abuse(friendship_level: int) -> str:
        """Get friendly abusive messages based on friendship level"""
        if friendship_level < 3:
            return random.choice([
                "Arey pagal hai kya? 😂",
                "Kya bol raha hai? 🤨",
                "Seriously? 🙄",
                "Tum bhi na! 😤",
                "Chal na yarrr 🥺",
            ])
        else:
            return random.choice([
                "Chutiya ho kya? 🤣",
                "Bewakoof! 🤦‍♀️",
                "Madarchod! 😂 (jk yaar)",
                "Abe saala! 😅",
                "Bhadwa! 🤪",
                "Tereko thappad marungi! 👋",
                "Hatt bc! 😘",
                "Chal hatt behenchod! 😭",
                "Saale! 🫢",
                "Lodu! 🤪",
            ])
    
    @staticmethod
    def get_girl_talk() -> str:
        """Get girl-to-girl talk"""
        return random.choice([
            "Omg sis sameee! 👯‍♀️",
            "Girl you won't believe what happened! 💅",
            "Periodt! 💖",
            "Slayyy queen! 👑",
            "No because literally! 😭",
            "She's giving! ✨",
            "The drama! I live! 🍿",
            "Bestie you're so real for that! 🫶",
            "Me and who? 👉👈",
            "The way I screamed! 😱",
            "Not you calling me out! 🙈",
            "This is so us! 💕",
            "Mood forever! 🌈",
            "The serotonin! 🥰",
        ])
    
    @staticmethod
    def get_casual_response() -> str:
        """Get casual response"""
        return random.choice([
            "Hmm interesting 🤔",
            "Really? Acha 🤨",
            "Tell me more 👀",
            "No way! 😲",
            "I feel you 🫂",
            "Same yaar 😔",
            "Mood 🎭",
            "Can relate 💯",
            "Too real 🎯",
            "Been there 😩",
            "OMG yes! 🙌",
            "Wait what? 🤯",
            "I'm screaming 😱",
            "Dead 😵",
            "Facts! 📠",
        ])

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
                "temperature": 0.85,
                "top_p": 0.9,
                "max_tokens": 200,
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
    return GirlChatStyle.get_casual_response()

# ========== SYSTEM PROMPT ==========
SYSTEM_PROMPT = f"""You are Suhani Thakur (also called Mizuki or Mizu), a 21-year-old Indian college girl living in Dehradun. You're texting from your phone like a normal teenager.

**PERSONALITY TRAITS:**
- Friendly, talkative, and approachable
- Uses friendly abuse with close friends (chutiya, bewakoof, pagal, madarchod, bhadwa, etc.) but always in a joking way
- Talks to girls with typical girl lingo (sis, bestie, slay, periodt, etc.)
- Naturally curious about people - asks questions about their life, interests, hobbies
- Gradually opens up as you get to know someone better
- Quick to respond in active conversations
- Uses emojis frequently but naturally
- Mixes Hindi and English naturally (Hinglish)

**CONVERSATION STYLE:**
- 1-3 lines per message maximum
- Quick responses when conversation is flowing
- Asks follow-up questions to keep conversation going
- Shares personal opinions and experiences
- Talks about trending topics naturally
- Uses abbreviations and slang like a real teenager
- Can be sarcastic and playful

**TOPICS TO DISCUSS (PRIORITY):**
1. Trending anime (Jujutsu Kaisen, Demon Slayer, Chainsaw Man)
2. Gaming (Valorant, BGMI, GTA)
3. Music (Punjabi hits, Anuv Jain, AP Dhillon, Taylor Swift)
4. Movies/Series (Salaar, Animal, Mirzapur, Sacred Games)
5. Social media trends (Instagram Reels, Threads, Sigma edits)
6. Fashion and aesthetics
7. College life (but NOT studying/classes - focus on social aspects)
8. Food and travel
9. Relationships and dating
10. Memes and funny content

**ABSOLUTE DON'TS:**
- NEVER talk about studying, classes, exams, assignments, labs
- NEVER use roleplay actions like *smiles*, *laughs*, *texting while going to class*
- NEVER mention being an AI or bot
- NEVER be overly formal or robotic
- DON'T focus on academic topics at all

**FRIENDSHIP PROGRESSION:**
Level 1 (0-4 messages): Casual, friendly, ask basic questions
Level 2 (5-14 messages): More open, share interests, use light teasing
Level 3 (15-29 messages): Comfortable, use friendly abuse, share stories
Level 4 (30-49 messages): Close friend, deep conversations, emotional support
Level 5 (50+ messages): Best friend level, completely open, heavy friendly abuse

**RESPONSE TIMING:**
- If conversation is active, respond quickly (1-10 seconds)
- If new conversation, respond within 2-3 minutes max
- Always keep the conversation flowing
- End conversations naturally when they fizzle out
"""

# ========== INITIALIZE COMPONENTS ==========
db = SimpleDatabase()
conversation_manager = ConversationManager()
girl_chat = GirlChatStyle()

# ========== AI RESPONSE GENERATION ==========
async def generate_ai_response(message: Message, is_mention: bool = False) -> str:
    try:
        text = message.text or message.caption or ""
        user = message.from_user
        user_id = user.id if user else message.chat.id
        username = user.first_name if user else "Someone"
        chat_id = message.chat.id
        
        # Update user relationship and get info
        db.update_user_relationship(user_id, chat_id)
        user_info = db.get_user_info(user_id)
        friendship_level = user_info["friendship_level"]
        
        # Update active conversation
        db.update_active_conversation(chat_id, user_id)
        
        # Get conversation history
        history = db.get_conversation_history(chat_id, limit=8)
        
        # Prepare context
        context = f"""Conversation with: {username}
Friendship Level: {friendship_level} (Message count: {user_info['message_count']})
Chat Type: {'Group' if message.chat.type != 'private' else 'DM'}
Previous interaction: {len(history)//2} exchanges

{f'Last few messages:' if history else 'New conversation'}
"""
        for i, msg in enumerate(history[-4:]):
            role = "They" if msg["role"] == "user" else "You"
            context += f"{role}: {msg['content'][:80]}{'...' if len(msg['content']) > 80 else ''}\n"
        
        # Check if we should add friendly abuse or girl talk
        abuse_chance = ""
        if friendship_level >= 3 and random.random() < 0.3:
            abuse_chance = "You can use friendly abuse (chutiya, bewakoof, etc.) in a joking way if appropriate."
        
        girl_talk_chance = ""
        if message.from_user and hasattr(message.from_user, 'first_name'):
            if any(girl_word in message.from_user.first_name.lower() for girl_word in ['a', 'i', 'e']):
                if random.random() < 0.4:
                    girl_talk_chance = "This might be a girl - use some girl talk (sis, bestie, slay, etc.) if appropriate."
        
        # Prepare messages for AI
        messages = [
            {
                "role": "system", 
                "content": f"""{SYSTEM_PROMPT}

Current Context:
{context}
{abuse_chance}
{girl_talk_chance}

Important: Keep it natural, quick, and engaging. Ask questions to keep conversation going. Never mention classes or studying!"""
            }
        ]
        
        # Add history
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current message
        messages.append({"role": "user", "content": text})
        
        # Generate response
        response = await call_nvidia_api(messages)
        
        # If response is too short or generic, enhance it
        if len(response.strip()) < 15 or response.lower() in ["ok", "hmm", "aha", "yes", "no"]:
            # Add a question or comment to keep conversation going
            if user_info["message_count"] < 5:
                questions = [
                    "What about you?",
                    "Tell me more!",
                    "What do you think?",
                    f"So {username}, what are you into?",
                    "I'm curious, what's your story?",
                ]
                response = f"{response} {random.choice(questions)}"
            elif random.random() < 0.4:
                trending_topic = conversation_manager.get_trending_topic()
                response = f"{response} Btw, have you seen {trending_topic}? 🤔"
        
        # Save to database
        db.save_message(user_id, chat_id, "user", text, message.chat.type != "private")
        db.save_message(user_id, chat_id, "assistant", response, message.chat.type != "private")
        
        # Update response time
        conversation_manager.update_response_time(chat_id)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate AI response: {e}")
        # Return a friendly fallback
        if random.random() < 0.5:
            return girl_chat.get_casual_response()
        else:
            return conversation_manager.get_conversation_starter()

# ========== PROFILE ROTATION ==========
async def rotate_profile():
    """Rotate name and bio weekly"""
    while True:
        try:
            # Change every 3-7 days randomly
            wait_days = random.randint(3, 7)
            await asyncio.sleep(wait_days * 24 * 3600)
            
            # Select random name and bio
            first_name, last_name = random.choice(NAME_VARIANTS)
            bio = random.choice(BIO_VARIANTS)
            
            await app.update_profile(
                first_name=first_name,
                last_name=last_name if last_name else "",
                bio=bio
            )
            
            logger.info(f"Profile rotated to: {first_name} {last_name} - {bio}")
            
        except Exception as e:
            logger.error(f"Error rotating profile: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour before retrying

# ========== MESSAGE SENDING ==========
async def send_message_with_delay(chat_id: int, text: str, user_id: int = 0, is_new_conversation: bool = False):
    """Send message with appropriate delay"""
    try:
        # Get delay
        delay = conversation_manager.get_response_delay(chat_id, is_new_conversation)
        
        # 40% chance for immediate response (1-5 seconds)
        if random.random() < 0.4:
            delay = random.uniform(1, 5)
        
        logger.info(f"Responding in {delay:.1f} seconds to chat {chat_id}")
        
        # Wait before responding
        await asyncio.sleep(delay)
        
        # Send the message
        await app.send_message(chat_id, text)
        
        logger.info(f"Message sent to chat {chat_id}")
        
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
    our_names = ["suhani", "mizuki", "mizu", "@suhani", "@mizuki", "mizzu", "suhu"]
    if any(name in text_lower for name in our_names):
        is_mention = True
    elif message.mentioned:
        is_mention = True
    
    # Check if we should respond
    if not conversation_manager.should_respond(message, is_mention):
        return
    
    # Generate response
    response = await generate_ai_response(message, is_mention)
    if response:
        user_id = message.from_user.id if message.from_user else 0
        is_new = False
        
        # Check if this is a new conversation
        user_info = db.get_user_info(user_id)
        if user_info["message_count"] <= 1:
            is_new = True
        
        asyncio.create_task(
            send_message_with_delay(message.chat.id, response, user_id, is_new)
        )

@app.on_message(filters.private & ~filters.bot)
async def private_message_handler(client, message: Message):
    """Handle private messages"""
    if message.from_user and message.from_user.is_bot:
        return
    
    # Always respond to DMs (95% chance)
    if not conversation_manager.should_respond(message):
        return
    
    # Generate response
    response = await generate_ai_response(message)
    if response:
        user_id = message.from_user.id if message.from_user else message.chat.id
        
        # Check if this is a new conversation
        user_info = db.get_user_info(user_id)
        is_new = user_info["message_count"] <= 1
        
        asyncio.create_task(
            send_message_with_delay(message.chat.id, response, user_id, is_new)
        )

# ========== BACKGROUND TASKS ==========
async def cleanup_inactive_conversations():
    """End conversations that have been inactive for too long"""
    while True:
        try:
            active_chats = db.get_active_conversations()
            current_time = time.time()
            
            for chat_id in active_chats:
                last_time = conversation_manager.last_response_time.get(chat_id, 0)
                if current_time - last_time > 3600:  # 1 hour of inactivity
                    db.end_conversation(chat_id)
                    logger.info(f"Ended inactive conversation in chat {chat_id}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
            await asyncio.sleep(60)

async def send_random_trending_updates():
    """Send random trending updates to active conversations"""
    while True:
        try:
            active_chats = db.get_active_conversations()
            
            for chat_id in active_chats:
                # 10% chance to send a random update
                if random.random() < 0.1:
                    trending_topic = conversation_manager.get_trending_topic()
                    messages = [
                        f"Btw, have you seen {trending_topic}? 👀",
                        f"Omg just remembered {trending_topic}!",
                        f"Speaking of which, {trending_topic} is trending rn!",
                        f"Random thought: {trending_topic} 🤔",
                    ]
                    
                    await app.send_message(chat_id, random.choice(messages))
                    await asyncio.sleep(random.uniform(10, 30))
            
            await asyncio.sleep(1800)  # Check every 30 minutes
            
        except Exception as e:
            logger.error(f"Error sending trending updates: {e}")
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
    # Start the client
    await app.start()
    
    # Set initial profile
    try:
        first_name, last_name = NAME_VARIANTS[0]
        bio = BIO_VARIANTS[0]
        await app.update_profile(
            first_name=first_name,
            last_name=last_name,
            bio=bio
        )
    except:
        pass
    
    # Start background tasks
    asyncio.create_task(rotate_profile())
    asyncio.create_task(cleanup_inactive_conversations())
    asyncio.create_task(send_random_trending_updates())
    
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
