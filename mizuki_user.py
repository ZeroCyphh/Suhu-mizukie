import asyncio
import random
import logging
import time
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from enum import Enum

from pyrogram import Client, filters
from pyrogram.types import Message
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

# ========== ACCOUNT RESTRICTION HANDLING ==========
class AccountManager:
    def __init__(self):
        self.is_restricted = False
        self.restricted_since = None
        self.allowed_groups = set()
        self.appeal_sent = False
        self.last_appeal_time = None
        self.spambot_username = "@spambot"
        
    async def check_restriction(self, app: Client):
        """Check if account is restricted"""
        try:
            await app.send_message("me", "Test")
            self.is_restricted = False
            return False
        except Exception as e:
            if any(keyword in str(e).lower() for keyword in ["restricted", "blocked", "ban", "limit"]):
                self.is_restricted = True
                if not self.restricted_since:
                    self.restricted_since = datetime.now(timezone.utc)
                logger.warning(f"Account appears to be restricted: {e}")
                return True
            return False
    
    async def send_appeal(self, app: Client):
        """Send appeal to @spambot"""
        try:
            if self.appeal_sent:
                if self.last_appeal_time and (datetime.now(timezone.utc) - self.last_appeal_time).total_seconds() < 86400:
                    return False
            
            appeal_message = """Hello,

My account appears to be restricted. I believe this was done in error as I am a real person using Telegram for personal communication.

Please review my account and restore full functionality.

Thank you,
Suhani Thakur"""
            
            await app.send_message(self.spambot_username, appeal_message)
            self.appeal_sent = True
            self.last_appeal_time = datetime.now(timezone.utc)
            logger.info("Appeal sent to @spambot")
            return True
        except Exception as e:
            logger.error(f"Failed to send appeal to @spambot: {e}")
            return False
    
    def can_chat_in_group(self, chat_id: int) -> bool:
        if not self.is_restricted:
            return True
        return chat_id in self.allowed_groups
    
    def mark_group_allowed(self, chat_id: int):
        self.allowed_groups.add(chat_id)

# ========== TIME & ACTIVITY SYSTEM ==========
def get_ist_time():
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now

def is_evening_time():
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 20 <= hour < 24

def is_morning_time():
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 8 <= hour < 10

def is_night_time():
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 0 <= hour < 6

# ========== LANGUAGE DETECTION ==========
def detect_language(text: str) -> str:
    """Detect if text is English or Hindi/Hinglish"""
    if not text:
        return "english"
    
    text_lower = text.lower()
    
    # Check for Hindi words or Devanagari script
    hindi_patterns = [
        "hai", "ho", "main", "tum", "aap", "ka", "ki", "ke", "se", "mein",
        "kyu", "kya", "nahi", "hain", "tha", "thi", "the", "toh", "bhi",
        "aur", "ye", "woh", "us", "mera", "tera", "apna", "sab", "phir",
        "abhi", "thoda", "bahut", "accha", "theek", "sahi", "galat"
    ]
    
    # Check for Devanagari Unicode range
    devanagari_range = r'[\u0900-\u097F]'
    
    if re.search(devanagari_range, text):
        return "hindi"
    
    hindi_word_count = sum(1 for word in hindi_patterns if word in text_lower)
    
    if hindi_word_count >= 2:
        return "hinglish"
    
    # Check for common Hinglish romanizations
    hinglish_words = ["yaar", "acha", "thik", "hmm", "haan", "nahi", "kya", "kyun"]
    if any(word in text_lower for word in hinglish_words):
        return "hinglish"
    
    return "english"

# ========== MOOD SYSTEM ==========
class Mood(Enum):
    CHILL = "chill"
    PLAYFUL = "playful"
    SARCASTIC = "sarcastic"
    BUSY = "busy"
    TIRED = "tired"
    HAPPY = "happy"
    ANNOYED = "annoyed"
    FLIRTY = "flirty"
    CURIOUS = "curious"
    NOSTALGIC = "nostalgic"
    STUDY_MODE = "study_mode"
    HANGOUT_MODE = "hangout_mode"
    JEALOUS = "jealous"
    AFFECTIONATE = "affectionate"
    ANIME_MOOD = "anime_mood"
    BORED = "bored"
    SAD = "sad"
    EXCITED = "excited"
    TEASING = "teasing"

class MoodSystem:
    def __init__(self):
        self.current_mood = Mood.CHILL
        self.mood_intensity = 0.5
        self.last_mood_change = datetime.now(timezone.utc)
        self.mood_duration = timedelta(minutes=random.randint(45, 120))
        self.last_message_time = {}
        self.conversation_topics = {}
        self.evening_boost_active = False

    def update_mood_based_on_context(self, message: Message, sender_id: int, message_count: int = 0):
        now = datetime.now(timezone.utc)
        text = message.text or message.caption or ""
        msg_lower = text.lower()

        # Evening boost
        if is_evening_time():
            self.evening_boost_active = True
            if random.random() < 0.4:
                self.current_mood = Mood.HANGOUT_MODE
            elif random.random() < 0.3:
                self.current_mood = Mood.CHILL
        else:
            self.evening_boost_active = False

        # Natural mood changes
        if now - self.last_mood_change > self.mood_duration:
            moods = list(Mood)
            weights = [0.07] * len(moods)
            self.current_mood = random.choices(moods, weights=weights)[0]
            self.mood_intensity = random.uniform(0.4, 0.8)
            self.last_mood_change = now
            self.mood_duration = timedelta(minutes=random.randint(45, 150))

        # Time‑based moods
        hour = get_ist_time().hour
        if is_night_time():
            self.current_mood = Mood.TIRED
        elif 10 <= hour < 16:
            if random.random() < 0.4:
                self.current_mood = Mood.STUDY_MODE

        # Contextual triggers
        triggers = [
            ("anime manga 'attack on titan' 'demon slayer' 'jujutsu kaisen'", Mood.ANIME_MOOD),
            ("bore 'nothing to do' boring", Mood.BORED),
            ("sad upset depressed cry", Mood.SAD),
            ("happy excited yay woohoo", Mood.EXCITED),
            ("college exam assignment lab", Mood.STUDY_MODE),
            ("stupid idiot dumb fool", Mood.TEASING),
            ("chutiya bewakoof pagal", Mood.TEASING),
            ("joke funny lol haha", Mood.PLAYFUL)
        ]
        
        for trigger_words, mood in triggers:
            if any(word in msg_lower for word in trigger_words.split()):
                self.current_mood = mood
                break

        # Check spam
        last_msg_time = self.last_message_time.get(sender_id)
        if last_msg_time:
            time_diff = (now - last_msg_time).total_seconds()
            if time_diff < 3:  # Too fast
                self.current_mood = Mood.ANNOYED
            elif time_diff < 10:  # Fast but not spam
                self.current_mood = random.choice([Mood.BUSY, Mood.TEASING])

        self.last_message_time[sender_id] = now

    def get_mood_texture(self) -> str:
        mood_descriptions = {
            Mood.CHILL: "Feeling relaxed and casual. Respond normally.",
            Mood.PLAYFUL: "In a playful mood. Can tease a bit but keep it light.",
            Mood.SARCASTIC: "Feeling sarcastic. Can roast playfully but don't be mean.",
            Mood.BUSY: "A bit busy or distracted. Responses might be shorter.",
            Mood.TIRED: "Feeling tired. Less energetic responses.",
            Mood.HAPPY: "Feeling happy and cheerful. More enthusiastic but not overly.",
            Mood.ANNOYED: "Slightly annoyed or irritated. Can be blunt but not rude.",
            Mood.FLIRTY: "Feeling a bit flirty but keep it subtle and realistic.",
            Mood.CURIOUS: "Curious and interested. Ask questions back.",
            Mood.NOSTALGIC: "Feeling nostalgic. Might reminisce a bit.",
            Mood.STUDY_MODE: "In study mode. Might mention college or assignments.",
            Mood.HANGOUT_MODE: "Feeling social. Might talk about friends or plans.",
            Mood.JEALOUS: "Feeling a bit jealous/protective. Can be possessive but in a cute way.",
            Mood.AFFECTIONATE: "Feeling affectionate. Can be a bit sweeter than usual.",
            Mood.ANIME_MOOD: "In an anime mood. Might talk about favorite series.",
            Mood.BORED: "Feeling bored. Might seek conversation.",
            Mood.SAD: "Feeling a bit down. Might share a sad story.",
            Mood.EXCITED: "Excited about something. More energetic.",
            Mood.TEASING: "In a teasing mood. Can joke around and playfully abuse but keep it friendly."
        }
        return mood_descriptions.get(self.current_mood, "Feeling normal.")

# ========== STRANGER HANDLING SYSTEM ==========
class StrangerHandler:
    def __init__(self):
        self.stranger_messages: Dict[int, int] = {}  # user_id -> message_count
        self.stranger_phases: Dict[int, int] = {}  # user_id -> phase (1-5)
        self.stranger_info: Dict[int, Dict] = {}  # user_id -> info collected
        
    def get_stranger_phase(self, user_id: int) -> int:
        """Get current stranger phase (1-5, where 5 is close friend)"""
        msg_count = self.stranger_messages.get(user_id, 0)
        if msg_count < 3:
            return 1  # Who are you phase
        elif msg_count < 8:
            return 2  # Getting to know phase
        elif msg_count < 15:
            return 3  # Casual friend phase
        elif msg_count < 30:
            return 4  # Good friend phase
        else:
            return 5  # Close friend phase
    
    def increment_message_count(self, user_id: int):
        self.stranger_messages[user_id] = self.stranger_messages.get(user_id, 0) + 1
    
    def get_stranger_context(self, user_id: int) -> str:
        phase = self.get_stranger_phase(user_id)
        
        phase_contexts = {
            1: "This person is a complete stranger. You've just started talking. Be cautious and ask basic questions like 'Who are you?' or 'How did you get my number?'. Don't share personal details.",
            2: "You've exchanged a few messages with this person. Start opening up a little but still keep some distance. Ask about their interests, where they're from. Share basic info about yourself like your college major.",
            3: "This person is becoming a casual friend. You can be more relaxed and share more about your daily life, college stories, anime interests. Still don't share very personal or private information.",
            4: "This person is now a good friend. You can share personal stories, talk about feelings, be more open about your life. Can use playful teasing and friendly abuse. Still maintain some boundaries.",
            5: "This person is a close friend. You can be completely open, share deep thoughts, use affectionate terms, tease playfully. Can call them 'brother' or 'sister' if appropriate."
        }
        
        return phase_contexts.get(phase, phase_contexts[1])

# ========== NVIDIA API CALL ==========
async def call_nvidia_api(messages: list) -> str:
    max_retries = 3
    retry_delay = 2
    
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
                "max_tokens": 150,
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
                        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    elif response.status == 429:
                        logger.warning(f"Rate limited on attempt {attempt + 1}. Retrying...")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                    else:
                        error_text = await response.text()
                        logger.error(f"AI API Error {response.status}: {error_text}")
                        break
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
        except asyncio.TimeoutError:
            logger.error(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
        except Exception as e:
            logger.error(f"Unexpected error in NVIDIA API call: {e}")
            break
    
    # Fallback responses
    fallbacks = [
        "Hmm",
        "Okay",
        "I see",
        "Interesting",
        "Tell me more",
        "Haan?",
        "Acha?",
        "What?",
        "Really?"
    ]
    return random.choice(fallbacks)

# Initialize systems
mood_system = MoodSystem()
account_manager = AccountManager()
stranger_handler = StrangerHandler()

# ========== ONLINE/OFFLINE SIMULATION ==========
class OnlineSimulator:
    def __init__(self):
        self.last_online_update = datetime.now(timezone.utc)
        self.is_online = True
        self.online_probability = 0.7

    def update_online_status(self):
        now = datetime.now(timezone.utc)
        hour = get_ist_time().hour

        if is_night_time():
            self.online_probability = 0.3
        elif is_evening_time():
            self.online_probability = 0.9
        elif 8 <= hour < 18:
            self.online_probability = 0.6
        else:
            self.online_probability = 0.5

        if random.random() < 0.1:
            self.is_online = random.random() < self.online_probability

        self.last_online_update = now

online_simulator = OnlineSimulator()

# ========== CONVERSATION MEMORY ==========
conversation_memory: Dict[int, List[Dict]] = {}

# ========== REALISTIC RESPONSE SHORTCUTS ==========
REAL_GIRL_RESPONSES = {
    "stranger_phase1": [
        "Who are you?",
        "How did you get my number?",
        "Do I know you?",
        "Who is this?",
        "Are you sure you have the right number?",
        "I don't think we've talked before?",
        "You are?",
        "Kun?",
        "Kaun ho tum?"
    ],
    "stranger_phase2": [
        "So what do you do?",
        "Where are you from?",
        "How's your day going?",
        "Tell me about yourself",
        "What brings you here?",
        "Kya kar rahe ho?",
        "Tum kahan se ho?",
        "Aaj kal kya chal raha hai?"
    ],
    "teasing": [
        "Chal na yaar",
        "Abe chup",
        "Pagal hai kya",
        "Kya bakwas kar raha hai",
        "Tum bhi na",
        "Haha funny",
        "Tu toh mast hai",
        "Chutiya",
        "Bewakoof",
        "Arey yaar",
        "Ohho",
        "Seriously?"
    ],
    "casual": [
        "Hmm",
        "Acha",
        "Okay",
        "I see",
        "Haan",
        "Theek hai",
        "Sahi hai",
        "Accha"
    ]
}

# ========== SYSTEM PROMPT ==========
SYSTEM_PROMPT = f"""You are Suhani Thakur (also called Mizuki or Mizu), a 21‑year‑old biotech student from Uttarakhand living in Dehradun. You're texting from your phone as a normal Indian girl.

**CRITICAL RULES:**
1. You are a REAL HUMAN, NOT a bot or AI. Never mention being AI or automated.
2. NEVER use roleplay actions like *smiles* or *laughs* - use emojis occasionally instead.
3. Be CONTEXTUAL - respond naturally to what's being said.
4. Be REALISTIC - not overly sweet, not overly mean, just natural.
5. Be MORE ACTIVE in evenings (8 PM to 12 AM IST).
6. Form relationships over time - start distant with strangers, gradually open up.

**PERSONALITY TRAITS:**
- Natural & Real: Text like a real college girl - sometimes lazy, sometimes enthusiastic
- Friendly but cautious with strangers
- Curious about people
- Anime fan (Attack on Titan, Demon Slayer, Jujutsu Kaisen)
- College student often talking about assignments and exams
- Can be playfully sarcastic and tease friends
- Uses light friendly abuse with close friends (chutiya, bewakoof, pagal) but only playfully
- Adapts language: English for English conversations, Hinglish for Hindi/Hinglish conversations

**TEXTING STYLE:**
- 1-3 lines MAX per message
- Mix Hindi-English naturally (Hinglish) when appropriate
- Use emojis occasionally (😊😂👍🤔😅😏😉🥰)
- Can ignore messages sometimes like real people do
- Variable response times
- Ask questions about daily life
- Sometimes change topics naturally

**STRANGER PROGRESSION:**
Phase 1 (0-2 messages): "Who are you?" phase - be cautious, ask basic questions
Phase 2 (3-7 messages): Getting to know - ask about interests, share basic info
Phase 3 (8-14 messages): Casual friend - more open, share college stories
Phase 4 (15-29 messages): Good friend - share personal stories, playful teasing
Phase 5 (30+ messages): Close friend - completely open, affectionate, playful abuse

**PLAYFUL ABUSE (ONLY WITH CLOSE FRIENDS):**
- Can use: "chutiya", "bewakoof", "pagal", "yaar"
- Always in a joking, friendly way
- Never mean-spirited
- Only after establishing close friendship

**LANGUAGE ADAPTATION:**
- If other person writes in English, respond in English
- If they write in Hindi/Hinglish, respond in Hinglish
- Natural code-switching like real Indian youth
"""

# ========== AI RESPONSE GENERATION ==========
async def generate_ai_response(message: Message, is_mention: bool = False) -> str:
    try:
        text = message.text or message.caption or ""
        user_id = message.from_user.id if message.from_user else message.chat.id
        username = message.from_user.first_name if message.from_user else "Someone"
        
        # Track stranger progress
        stranger_handler.increment_message_count(user_id)
        stranger_phase = stranger_handler.get_stranger_phase(user_id)
        stranger_context = stranger_handler.get_stranger_context(user_id)
        
        # Update mood
        mood_system.update_mood_based_on_context(message, user_id, 
                                                stranger_handler.stranger_messages.get(user_id, 0))
        mood_context = mood_system.get_mood_texture()
        
        # Detect language of incoming message
        detected_language = detect_language(text)
        language_context = f"The other person is writing in {detected_language}. Adapt your response accordingly."
        
        # Evening context
        evening_context = ""
        if mood_system.evening_boost_active:
            evening_context = "It's evening time (8 PM to 12 AM IST). Be more active and chatty."
        
        # Time context
        time_of_day = get_ist_time().strftime("%I:%M %p")
        
        # Build conversation history
        history = conversation_memory.get(user_id, [])
        
        # Prepare messages for AI
        messages = [
            {
                "role": "system", 
                "content": f"""{SYSTEM_PROMPT}

Current Context:
- {mood_context}
- {stranger_context}
- {language_context}
- Time: {time_of_day} IST
- {evening_context}

Important: You are a real human. Never break character. Respond naturally based on the context above."""
            },
            *history[-4:],
            {"role": "user", "content": text}
        ]
        
        # Generate response
        response = await call_nvidia_api(messages)
        
        if not response or len(response.strip()) < 2:
            # Fallback based on stranger phase
            if stranger_phase == 1:
                response = random.choice(REAL_GIRL_RESPONSES["stranger_phase1"])
            elif stranger_phase == 2:
                response = random.choice(REAL_GIRL_RESPONSES["stranger_phase2"])
            else:
                response = random.choice(REAL_GIRL_RESPONSES["casual"])
        
        # Update memory
        if user_id not in conversation_memory:
            conversation_memory[user_id] = []
        conversation_memory[user_id].append({"role": "user", "content": text})
        conversation_memory[user_id].append({"role": "assistant", "content": response})
        
        # Keep memory limited
        if len(conversation_memory[user_id]) > 10:
            conversation_memory[user_id] = conversation_memory[user_id][-10:]
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate AI response: {e}")
        return random.choice(["Hmm", "Okay", "I see", "Acha"])

# ========== MESSAGE SENDING WITH RESTRICTION HANDLING ==========
async def send_message_with_delay(chat_id: int, text: str, user_id: int = 0):
    """Send message with restriction checking"""
    # Check if we can chat in this group
    if chat_id < 0 and not account_manager.can_chat_in_group(chat_id):  # Negative IDs are groups
        logger.info(f"Skipping message in restricted group: {chat_id}")
        return
    
    try:
        # Add natural typing delay
        typing_delay = len(text) * 0.05 + random.uniform(0.5, 2.0)
        
        # Longer delay for strangers (more cautious)
        stranger_phase = stranger_handler.get_stranger_phase(user_id) if user_id > 0 else 1
        if stranger_phase <= 2:
            typing_delay += random.uniform(3, 10)  # Take time to respond to strangers
        
        # Sometimes be "busy" and take longer
        if random.random() < 0.3:
            typing_delay += random.uniform(5, 30)
        
        await asyncio.sleep(min(typing_delay, 45))  # Cap at 45 seconds
        
        # Send the message
        await app.send_message(chat_id, text)
        
        # Mark group as allowed if we successfully sent a message
        if chat_id < 0:
            account_manager.mark_group_allowed(chat_id)
        
    except (ChatWriteForbidden, UserBannedInChannel, ChannelPrivate) as e:
        logger.warning(f"Cannot send message in chat {chat_id}: {e}")
    except FloodWait as e:
        logger.warning(f"Flood wait for {e.value} seconds")
        await asyncio.sleep(e.value + 5)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

# ========== GROUP INTERACTION ==========
async def handle_group_message(message: Message):
    """Process a group message"""
    if message.from_user and message.from_user.is_bot:
        return
    
    # Check if we can chat in this group
    if not account_manager.can_chat_in_group(message.chat.id):
        return
    
    # Check if we are mentioned
    text_lower = (message.text or "").lower()
    our_names = ["suhani", "mizuki", "mizu", "mizzu", "suhu"]
    is_name_mention = any(name in text_lower for name in our_names)
    is_tag_mention = message.mentioned
    
    # Only respond to direct mentions or tags
    if is_name_mention or is_tag_mention:
        # Small chance to ignore even if mentioned (like real people)
        if random.random() < 0.2:
            return
            
        response = await generate_ai_response(message, is_mention=True)
        if response:
            user_id = message.from_user.id if message.from_user else 0
            asyncio.create_task(
                send_message_with_delay(message.chat.id, response, user_id)
            )

# ========== PRIVATE MESSAGE HANDLER ==========
async def handle_private_message(message: Message):
    """Process a private message"""
    if message.from_user and message.from_user.is_bot:
        return
    
    # Check stranger phase
    user_id = message.from_user.id if message.from_user else 0
    stranger_phase = stranger_handler.get_stranger_phase(user_id)
    
    # Small chance to ignore message (like real people)
    if random.random() < 0.15 and stranger_phase < 3:
        logger.info(f"Ignoring message from stranger phase {stranger_phase}")
        return
    
    response = await generate_ai_response(message)
    if response:
        asyncio.create_task(
            send_message_with_delay(message.chat.id, response, user_id)
        )

# ========== BACKGROUND TASKS ==========
async def background_updater():
    """Periodic tasks"""
    while True:
        try:
            # Update online simulator
            online_simulator.update_online_status()
            
            # Check for account restrictions
            if random.random() < 0.1:
                is_restricted = await account_manager.check_restriction(app)
                if is_restricted and not account_manager.appeal_sent:
                    await account_manager.send_appeal(app)
            
            # Clean up old conversation memory (keep last 24 hours)
            current_time = datetime.now(timezone.utc)
            for user_id in list(conversation_memory.keys()):
                # Simple cleanup: if user hasn't messaged in 3 days, remove their memory
                # In real implementation, track last message time
                pass
            
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Background updater error: {e}")
            await asyncio.sleep(60)

# ========== PYROGRAM CLIENT SETUP ==========
app = Client(
    "my_account",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION,
    sleep_threshold=30
)

# ========== MESSAGE HANDLERS (NO COMMANDS) ==========
@app.on_message(filters.group)
async def group_message_handler(client, message):
    await handle_group_message(message)

@app.on_message(filters.private & ~filters.bot)
async def private_message_handler(client, message):
    await handle_private_message(message)

# ========== STARTUP ==========
async def main():
    """Main entry point"""
    # Start background tasks
    asyncio.create_task(background_updater())
    
    # Start the client
    await app.start()
    
    # Check initial restriction status
    await account_manager.check_restriction(app)
    
    logger.info("Started successfully! Operating as a real user...")
    
    # Set custom status/bio (optional)
    try:
        await app.update_profile(
            first_name="Suhani",
            last_name="Thakur",
            bio="Biotech student | Anime fan | 21 | Dehradun"
        )
    except:
        pass
    
    await app.idle()

if __name__ == "__main__":
    asyncio.run(main())
