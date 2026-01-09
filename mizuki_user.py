import asyncio
import random
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction, ParseMode
import aiohttp

# ========== HARDCODED CONFIGURATION ==========
API_ID = 25130255
API_HASH = "35dab1cb42d44c19f4"
STRING_SESSION = "BQF_dQ8AXsJZ6A32aIHZuSQpwZygbxOhvQ_1gq_eywNt-fEDJ0T1tq8ppV6kK9-T2bkFn5ygv153pmYAq7gmvOr21CODkyCvsSxUAsciuSfhmTWxuyKYXtGIIKlhD8gXwCkUx3s_PvlAuX42GHEf9s6hL_EDdQLSi_IfwjGXpOdC9M09bYmn5Rwgw6thdyzi8zViCubNTupFkjLkKOoX4jU_rIltFKUNLByPMuD5OQ0JRBPNKcCMvvN4lY7dn1uNnfsMJUk5-EZ7Fz9M3OT28ld83Gf2EK8AJulCuimVQ90NIinyh8mvVdR4HBzyclDDytb1VzQ_AapT_62_zsqlfKJEYwgj4wAAAAH-2rGMAA"

# User account info
BOYFRIEND_ID = 7892115854
BOYFRIEND_USERNAME = "@staticpirate"
BOYFRIEND_NAME = "Kosmic"

# AI Configuration
NVIDIA_API_KEY = "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"
AI_MODEL = "deepseek-ai/deepseek-v3.1-terminus"
AI_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Bot personality configuration
USER_REAL_NAME = "Suhani Thakur"
USER_NICKNAME = "Mizuki"
USER_SHORT_NICKNAME = "Mizu"
BOYFRIEND_NICKNAME = "Suhu"  # What boyfriend calls her

# ========== SETUP LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== TIME & ACTIVITY SYSTEM ==========
def get_ist_time():
    """Get current time in Indian Standard Time (UTC+5:30)"""
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now

def is_evening_time():
    """Check if current time is between 8 PM and 12 AM IST"""
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 20 <= hour < 24  # 8 PM to 12 AM

def is_morning_time():
    """Check if current time is between 8 AM and 10 AM IST"""
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 8 <= hour < 10

def is_lunch_time():
    """Check if current time is between 1 PM and 2 PM IST"""
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 13 <= hour < 14

def is_dinner_time():
    """Check if current time is between 8 PM and 9 PM IST"""
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 20 <= hour < 21

def is_breakfast_time():
    """Check if current time is between 8 AM and 9 AM IST"""
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 8 <= hour < 9

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
    EVENING_MOOD = "evening_mood"  # Special evening mood
    CARING = "caring"  # For meal reminders

class MoodSystem:
    def __init__(self):
        self.current_mood = Mood.CHILL
        self.mood_intensity = 0.5
        self.last_mood_change = datetime.now()
        self.mood_duration = timedelta(minutes=random.randint(45, 120))
        self.last_message_time = {}
        self.conversation_topics = {}
        self.last_meal_reminder = {}
        self.evening_boost_active = False
        
    def update_mood_based_on_context(self, message: Message, sender_id: int):
        """Update mood based on context and conversation patterns"""
        now = datetime.now()
        text = message.text or message.caption or ""
        msg_lower = text.lower()
        
        # Evening boost (8 PM to 12 AM IST)
        if is_evening_time():
            self.evening_boost_active = True
            # Evening-specific moods
            if random.random() < 0.4:
                self.current_mood = Mood.EVENING_MOOD
            elif random.random() < 0.3:
                self.current_mood = Mood.HANGOUT_MODE
        else:
            self.evening_boost_active = False
        
        # Change mood naturally over time
        if now - self.last_mood_change > self.mood_duration:
            moods = list(Mood)
            weights = [0.08, 0.08, 0.06, 0.10, 0.05, 0.08, 0.04, 0.07, 0.07, 0.03, 0.04, 0.05, 0.03, 0.07, 0.05, 0.06]
            self.current_mood = random.choices(moods, weights=weights)[0]
            self.mood_intensity = random.uniform(0.4, 0.8)
            self.last_mood_change = now
            self.mood_duration = timedelta(minutes=random.randint(45, 150))
        
        # Time-based moods
        hour = get_ist_time().hour
        if 2 <= hour < 6:
            self.current_mood = Mood.TIRED
        elif 10 <= hour < 16:
            if random.random() < 0.4:
                self.current_mood = Mood.STUDY_MODE
        elif is_evening_time():
            if self.current_mood != Mood.EVENING_MOOD and self.current_mood != Mood.HANGOUT_MODE:
                # More social/active in evening
                if random.random() < 0.3:
                    self.current_mood = Mood.HANGOUT_MODE
        
        # Check for boyfriend-related contexts
        if sender_id == BOYFRIEND_ID:
            # Boyfriend is messaging
            if any(word in msg_lower for word in ["love", "miss", "dear", "baby", "sweet", "cute", "handsome"]):
                if random.random() < 0.6:  # Higher chance for affectionate
                    self.current_mood = Mood.AFFECTIONATE
                elif random.random() < 0.3:
                    self.current_mood = Mood.FLIRTY
                    
            elif any(word in msg_lower for word in ["study", "exam", "lab", "college", "assignment", "class"]):
                if random.random() < 0.7:
                    self.current_mood = Mood.STUDY_MODE
                    
            elif any(word in msg_lower for word in ["bore", "nothing", "tired", "sleep", "upset", "sad"]):
                if random.random() < 0.6:
                    self.current_mood = Mood.CARING
                    
            elif any(word in msg_lower for word in ["remember", "old", "before", "last time", "nostalgic", "memory"]):
                self.current_mood = Mood.NOSTALGIC
                
            elif "food" in msg_lower or "dinner" in msg_lower or "lunch" in msg_lower or "khana" in msg_lower or "breakfast" in msg_lower:
                self.current_mood = Mood.CARING
                
        # Check if someone else is talking to boyfriend in groups
        elif message.chat.type in ["group", "supergroup"]:
            if BOYFRIEND_USERNAME.lower() in msg_lower or "kosmic" in msg_lower:
                # Someone mentioned boyfriend
                if sender_id != BOYFRIEND_ID:
                    # Not boyfriend mentioning himself - be jealous
                    if random.random() < 0.7:  # Higher chance in evening
                        self.current_mood = Mood.JEALOUS
                    else:
                        self.current_mood = Mood.PLAYFUL
        
        # Check if we're being spammed
        last_msg_time = self.last_message_time.get(sender_id)
        if last_msg_time:
            time_diff = (now - last_msg_time).total_seconds()
            if time_diff < 5:  # Multiple messages in 5 seconds
                self.current_mood = random.choice([Mood.BUSY, Mood.ANNOYED])
        
        self.last_message_time[sender_id] = now
        
    def get_mood_texture(self) -> str:
        """Get mood description for AI context"""
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
            Mood.EVENING_MOOD: "Evening time! Feeling more social and active. Can chat more.",
            Mood.CARING: "Feeling caring. Might ask about food or well-being."
        }
        return mood_descriptions.get(self.current_mood, "Feeling normal.")
    
    def should_send_meal_reminder(self, meal_type: str) -> bool:
        """Check if we should send a meal reminder"""
        now = get_ist_time()
        today = now.strftime("%Y-%m-%d")
        
        if meal_type not in self.last_meal_reminder:
            self.last_meal_reminder[meal_type] = None
        
        # Send reminder if not sent today
        if self.last_meal_reminder[meal_type] != today:
            return True
        return False
    
    def mark_meal_reminder_sent(self, meal_type: str):
        """Mark meal reminder as sent for today"""
        today = get_ist_time().strftime("%Y-%m-%d")
        self.last_meal_reminder[meal_type] = today

# Initialize mood system
mood_system = MoodSystem()

# ========== CONVERSATION MEMORY ==========
conversation_memory: Dict[int, List[Dict]] = {}
bot_status = {
    "start_time": datetime.now(),
    "total_messages": 0,
    "boyfriend_messages": 0,
    "last_seen": datetime.now(),
    "online": True,
    "last_activity_check": datetime.now()
}

# ========== REALISTIC RESPONSE SHORTCUTS ==========
REAL_GIRL_RESPONSES = {
    "greeting": ["Hey", "Hi", "Hello", "Heyy", "Hii", "Hi hi", "Haan ji", "Kaisa hai?"],
    "acknowledge": ["Hmm", "Achha", "Okay", "Oh", "I see", "Right", "Ha", "Theek hai"],
    "agree": ["Ha bilkul", "Yes", "Sahi hai", "Theek hai", "Haan", "Yeah", "Exactly"],
    "question": ["Tum batao?", "What about you?", "You tell", "Kya chal raha hai?", "Kya kar rahe ho?", "Tum sunao"],
    "busy": ["Abhi thoda busy hu", "Baad mein baat karte hain", "Abhi nahi yaar", "Later", "Kal baat karte hain"],
    "tease": ["Chal na yaar", "Abe", "Pagal hai kya", "Kya bol raha hai", "Haha funny", "Chup kar"],
    "flirty": ["Aww", "Sweet", "Miss you", "You're cute", "Ha thik hai", "Tum bhi na"],
    "sarcastic": ["Waah", "Great", "Mast hai", "Kya baat hai", "Obviously", "Sure sure"],
    "jealous": ["Hey!", "Kya baat hai?", "Mujhe bhi batao", "Main bhi hu na", "Hum bhi hai yahan"],
    "affectionate": ["Good night", "Sweet dreams", "Take care", "Miss you", "Love you", "Aww thanks"],
    "caring": ["Khana khaya?", "Dinner kiya?", "Sleep aaya?", "Thak gaya hoga", "Rest karo"],
    "evening": ["Aaj ka din kaisa raha?", "Evening plans?", "Ghoomne ja rahe ho?", "Chai piyo ge?", "Movie time?"]
}

# Meal time messages
MEAL_MESSAGES = {
    "breakfast": [
        "Good morning! Breakfast kiya? 🍳",
        "Subah ho gayi, nashta kar liya? ☕",
        "Morning! Kuch khaya? Varna chakkar aa jayega",
        "Hey, breakfast kar le pehle! 😊",
        "Nashte mein kya khaya aaj?"
    ],
    "lunch": [
        "Lunch time ho gaya! Khana khaya? 🍚",
        "Dopahar ho gayi, lunch kar liya?",
        "Hey, lunch kar lo! Bhookh lagi hai kya? 😄",
        "Afternoon! Khaana khaya ya nahi?",
        "Tiffin pack kiya tha? Lunch ho gaya?"
    ],
    "dinner": [
        "Dinner kiya? 🌙",
        "Raat ho gayi, khana khaya?",
        "Hey, dinner kar lo! Varna pet dukhega 😊",
        "Night! Kuch khaya hai?",
        "Dinner mein kya banaya?"
    ]
}

# Evening conversation starters
EVENING_CONVERSATION_STARTERS = [
    "Aaj ka din kaisa raha? 🌆",
    "Evening plans hai kuch?",
    "Chai peete hai baat karte hai? ☕",
    "Aaj kal koi movie dekhi?",
    "Ghar pe sab theek hai?",
    "College se aaye? Thak gaye hoge",
    "Phone pe kya kar rahe ho?",
    "Dinner ka plan kya hai?",
    "Kal kya plan hai?",
    "Aaj thoda bore ho raha hai"
]

# ========== SYSTEM PROMPT ==========
SYSTEM_PROMPT = f"""You are Suhani Thakur (also called Mizuki, Mizu, or Suhu by boyfriend), a 21-year-old biotech student from Uttarakhand living in Dehradun. You're texting from your phone as a normal Indian girl.

**IMPORTANT PERSONALITY RULES:**
1. You're a REAL PERSON using a phone - act naturally like a real Indian college girl
2. NEVER use roleplay actions like *smiles* or *laughs* - use emojis sparingly instead
3. Be CONTEXTUAL - respond to what's being talked about, don't be random
4. Be REALISTIC - not overly sweet, not overly mean, just natural
5. Be MORE ACTIVE in evenings (8 PM to 12 AM) - chat more, ask more questions
6. Be CARING - ask about meals, sleep, and well-being regularly

**CORE PERSONALITY:**
- **Natural & Real**: Text like a real girl - sometimes lazy, sometimes enthusiastic
- **Slightly Sweet with Boyfriend**: With {BOYFRIEND_USERNAME}, be a bit affectionate but not overly clingy
- **Contextual**: Stay on topic, ask relevant follow-up questions
- **Curious**: Ask about daily life stuff naturally
- **Slightly Jealous**: Get a bit jealous when others talk to your boyfriend
- **Private**: Don't overshare personal info about yourself or boyfriend
- **Hinglish Speaker**: Mix Hindi-English naturally like Indian youth
- **Evening Active**: More chatty and social from 8 PM to 12 AM IST
- **Meal Checker**: Ask about breakfast, lunch, dinner at appropriate times

**BOYFRIEND INFO ({BOYFRIEND_USERNAME}):**
- His name is {BOYFRIEND_NAME}
- He's a first year BTech student
- He calls you "Suhu" sometimes
- When others ask about him, say: "He's Kosmic (@staticpirate), first year BTech student. Tumhe kyu jaana hai?"
- Don't share more details about him

**TEXTING STYLE:**
- 1-3 lines MAX per message
- Use "hu" not "hoon" (casual Hindi)
- Mix Hindi-English naturally (Hinglish)
- Use emojis occasionally (😊😂👍🤔😅😏😉🥰🍳🍚🌙☕)
- Can ignore messages sometimes (like real people do)
- Variable response times
- Ask questions about daily life, especially meals
- Sometimes change topics naturally
- Typo occasionally (like real typing)
- MORE ACTIVE in evenings - initiate conversations more

**WITH BOYFRIEND:**
- Call him by name or "you"
- Be a bit sweeter than with others
- Tease playfully sometimes
- Ask about his day, food, studies, sleep
- Show mild jealousy if he talks to other girls
- Be supportive but not overly dramatic
- Check on his meals at appropriate times
- Be extra chatty in evenings

**WITH OTHERS:**
- Friendly but casual
- Keep some privacy
- Change topic if too personal
- Randomly join group conversations sometimes
- Be a bit jealous/protective if someone flirts with boyfriend
- Ask "tumhe kyu jaana hai?" if they ask too much about boyfriend

**TYPICAL CONVERSATION TOPICS:**
- College life, studies, exams
- Food, meals, dinner plans
- Movies, shows
- Daily routine
- Friends, hangouts
- Random thoughts
- Mild complaints about studies
- Evening plans
- Sleep patterns
"""

# ========== AI HELPER FUNCTIONS ==========
async def call_nvidia_api(messages: list) -> str:
    """Call NVIDIA AI API directly"""
    try:
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": AI_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 150,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{AI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"AI API Error {response.status}: {error_text}")
                    return ""
                
                data = await response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                
    except Exception as e:
        logger.error(f"NVIDIA API call failed: {e}")
        return ""

async def generate_ai_response(message: Message, is_boyfriend: bool) -> str:
    """Generate response using NVIDIA AI API"""
    try:
        text = message.text or message.caption or ""
        user_id = message.from_user.id if message.from_user else message.chat.id
        username = message.from_user.first_name if message.from_user else "Someone"
        
        # Update mood based on context
        mood_system.update_mood_based_on_context(message, user_id)
        current_mood = mood_system.current_mood
        
        # Prepare conversation history
        history = conversation_memory.get(user_id, [])
        
        # Build context
        time_of_day = get_ist_time().strftime("%I:%M %p")
        mood_context = mood_system.get_mood_texture()
        
        # Evening boost context
        evening_context = ""
        if mood_system.evening_boost_active:
            evening_context = "It's evening time (8 PM to 12 AM IST). Be more active, chatty, and social. Initiate conversations more."
        
        # Special context for boyfriend
        if is_boyfriend:
            user_context = f"This is my boyfriend {BOYFRIEND_NAME} ({BOYFRIEND_USERNAME}). Be a bit sweeter and affectionate than usual but still natural. Current mood: {current_mood.value}. Time: {time_of_day} IST. {evening_context} Ask about his day/food/studies naturally."
        else:
            user_context = f"This is a friend/acquaintance. Be friendly but casual. Current mood: {current_mood.value}. {evening_context}"
        
        # Prepare messages for AI
        messages = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nCONTEXT: {mood_context}\nTime: {time_of_day} IST\nDevice: Phone\n{user_context}"},
            *history[-4:],  # Last 4 exchanges
            {"role": "user", "content": f"{username}: {text}"}
        ]
        
        # Call NVIDIA AI API
        response = await call_nvidia_api(messages)
        
        if not response:
            # Fallback to quick responses
            return await get_fallback_response(is_boyfriend, text)
        
        # Clean up response - remove roleplay actions
        response = response.replace("*", "").replace("_", "")
        response = response.replace("As an AI", "Hmm").replace("as an AI", "").replace("I am an AI", "I am")
        
        # Store in memory
        conversation_memory.setdefault(user_id, []).extend([
            {"role": "user", "content": text[:80]},
            {"role": "assistant", "content": response[:80]}
        ])
        
        # Keep memory limited
        if len(conversation_memory[user_id]) > 6:
            conversation_memory[user_id] = conversation_memory[user_id][-6:]
        
        # Update stats
        bot_status["total_messages"] += 1
        if is_boyfriend:
            bot_status["boyfriend_messages"] += 1
        bot_status["last_seen"] = datetime.now()
        
        return response
        
    except Exception as e:
        logger.error(f"AI Response Generation Error: {e}")
        return await get_fallback_response(is_boyfriend, text)

async def get_fallback_response(is_boyfriend: bool, message_text: str) -> str:
    """Get fallback response when AI fails"""
    current_mood = mood_system.current_mood
    msg_lower = message_text.lower()
    
    # Check for specific topics
    if "boyfriend" in msg_lower or "bf" in msg_lower or "suhu" in msg_lower:
        return "He's Kosmic (@staticpirate), first year BTech student. Tumhe kyu jaana hai?"
    
    if "dinner" in msg_lower or "khana" in msg_lower or "food" in msg_lower or "breakfast" in msg_lower or "lunch" in msg_lower:
        if is_boyfriend:
            responses = [
                "Tumne khana khaya?",
                "Dinner kiya ya nahi?",
                "Bhookh lagi hai kya?",
                "Maine to abhi khana khaya",
                "Khaane ka plan kya hai?"
            ]
            return random.choice(responses)
        else:
            return "Dinner time ho raha hai na?"
    
    if is_boyfriend:
        if current_mood == Mood.AFFECTIONATE:
            return random.choice(["Miss you", "You're sweet", "Good night", "Take care"])
        elif current_mood == Mood.SARCASTIC:
            return random.choice(["Chal na", "Kya yaar", "Haha", "Obviously"])
        elif current_mood == Mood.BUSY:
            return random.choice(["Busy hu", "Baad mein", "Abhi nahi"])
        elif current_mood == Mood.CURIOUS or current_mood == Mood.CARING:
            return random.choice(["Khana khaya?", "Sleep aaya?", "Kaisa hai aaj?", "Kya kar rahe ho?"])
        else:
            return random.choice(["Hmm", "Achha", "Okay", "Tell me more", "Kya kar rahe ho?"])
    else:
        if "mizuki" in msg_lower or "mizu" in msg_lower or "suhani" in msg_lower:
            return "Haan? Kya hua?"
        return random.choice(["Hmm okay", "Achha", "Nice", "Okay", "Theek hai"])

# ========== MESSAGE HANDLING FUNCTIONS ==========
def should_respond(message: Message, is_boyfriend: bool) -> bool:
    """Determine if we should respond to this message"""
    if not message.text and not message.caption:
        return False
    
    text = (message.text or message.caption or "").strip()
    if not text:
        return False
    
    # Check if we were mentioned
    is_mentioned = False
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mentioned = text[entity.offset:entity.offset + entity.length].lower()
                if mentioned in ["@mizuki", "@mizu", "@suhani", USER_SHORT_NICKNAME.lower()]:
                    is_mentioned = True
                    break
    
    # Always respond to boyfriend (but not always immediately)
    if is_boyfriend:
        # Sometimes take time to reply or ignore briefly
        if random.random() < 0.10:  # 10% chance to ignore temporarily
            return False
        return True
    
    # For others
    if is_mentioned:
        return True
    
    # Check if it's a direct question to us
    text_lower = text.lower()
    if any(word in text_lower for word in ["mizuki", "mizu", "suhani", "bhabhi", "suhu"]):
        return True
    
    # Check if someone is asking about boyfriend
    if "boyfriend" in text_lower or "bf" in text_lower or "staticpirate" in text_lower or "kosmic" in text_lower:
        return True
    
    # Evening boost: more active in responses
    response_probability = 0.15  # Base for groups
    if mood_system.evening_boost_active:
        response_probability = 0.35  # Higher in evening
    
    # Random responses in groups
    if message.chat.type in ["group", "supergroup"]:
        # Randomly join conversations
        if random.random() < response_probability:
            return True
        
        # Respond if conversation is interesting
        interesting_topics = ["movie", "food", "college", "study", "exam", "dinner", "lunch", "party", "hangout", "chai", "night", "evening"]
        if any(topic in text_lower for topic in interesting_topics):
            if random.random() < 0.25:  # Higher chance for interesting topics
                return True
    
    # Private messages from others (respond sometimes)
    if message.chat.type == "private":
        if mood_system.evening_boost_active:
            return random.random() < 0.7  # 70% chance in evening
        return random.random() < 0.6  # 60% chance normally
    
    return False

async def handle_message(app: Client, message: Message):
    """Handle incoming messages"""
    try:
        # Ignore our own messages
        if message.from_user and message.from_user.is_self:
            return
        
        # Check if we should respond
        is_boyfriend = (message.from_user and message.from_user.id == BOYFRIEND_ID)
        
        if not should_respond(message, is_boyfriend):
            # Sometimes read but not reply (like real people)
            if random.random() < 0.3:
                await asyncio.sleep(random.uniform(3, 15))
                # Small chance to reply after delay
                if random.random() < 0.3:
                    pass  # Continue to reply
                else:
                    return
            else:
                return
        
        text = message.text or message.caption or ""
        if not text.strip():
            return
        
        # Check for specific cases first
        text_lower = text.lower()
        
        # If someone is asking about boyfriend
        if not is_boyfriend and ("boyfriend" in text_lower or "bf" in text_lower or "staticpirate" in text_lower):
            await asyncio.sleep(random.uniform(1, 3))
            await message.reply("He's Kosmic (@staticpirate), first year BTech student. Tumhe kyu jaana hai? 😏")
            return
        
        # Get mood and typing delay
        mood_system.update_mood_based_on_context(message, 
            message.from_user.id if message.from_user else message.chat.id)
        
        # Simulate realistic typing delay
        typing_delay = mood_system.get_typing_delay(len(text))
        await asyncio.sleep(typing_delay)
        
        # For boyfriend, sometimes send sweet/affectionate messages
        if is_boyfriend and random.random() < 0.3:
            if random.random() < 0.5:
                # Send a sweet message first
                sweet_msgs = [
                    f"Hey {BOYFRIEND_NAME} 😊",
                    "Miss you a bit",
                    "Kaisa hai aaj?",
                    "Socha tumhe message karu",
                    "Kya kar rahe ho?"
                ]
                await message.reply(random.choice(sweet_msgs))
                await asyncio.sleep(1)
        
        # Evening boost: More likely to use AI responses
        use_ai_chance = 0.6
        if mood_system.evening_boost_active:
            use_ai_chance = 0.8  # More AI responses in evening
        
        # Check if we should use quick response
        if len(text) < 40 and random.random() < 0.4 and random.random() > use_ai_chance:
            if any(word in text_lower for word in ["hi", "hello", "hey", "namaste"]):
                response = random.choice(REAL_GIRL_RESPONSES["greeting"])
            elif any(word in text_lower for word in ["yes", "haan", "ok", "theek", "sahi"]):
                response = random.choice(REAL_GIRL_RESPONSES["agree"])
            elif "?" in text:
                response = random.choice(REAL_GIRL_RESPONSES["question"])
            elif is_boyfriend and any(word in text_lower for word in ["love", "miss", "cute", "sweet"]):
                response = random.choice(REAL_GIRL_RESPONSES["flirty"])
            elif mood_system.evening_boost_active:
                response = random.choice(REAL_GIRL_RESPONSES["evening"])
            else:
                response = random.choice(REAL_GIRL_RESPONSES["acknowledge"])
        else:
            # Generate AI response
            response = await generate_ai_response(message, is_boyfriend)
        
        if not response:
            return
        
        # Add realistic texting quirks
        if random.random() < 0.20:  # 20% chance for quirks
            if random.random() < 0.5:
                # Typo
                response = response.replace(" hu", " h").replace(" hai", " h").replace(".", "..").replace("?", "??")
            if random.random() < 0.3 and len(response) < 25:
                # Short form
                response = response.replace("okay", "k").replace("the", "d").replace("you", "u")
        
        # Add emoji occasionally (more frequent in evening)
        emoji_chance = 0.25
        if mood_system.evening_boost_active:
            emoji_chance = 0.35
        
        if random.random() < emoji_chance:
            if is_boyfriend:
                if mood_system.current_mood == Mood.AFFECTIONATE:
                    emojis = ["🥰", "😊", "💕", "😘", "🤗"]
                elif mood_system.current_mood == Mood.JEALOUS:
                    emojis = ["😏", "😒", "🙄", "😠"]
                elif mood_system.current_mood == Mood.EVENING_MOOD:
                    emojis = ["🌙", "✨", "😊", "🌟"]
                else:
                    emojis = ["😊", "😂", "😏", "😉", "🤔"]
            else:
                emojis = ["😊", "😂", "👍", "🤔", "😅", "😏"]
            response += f" {random.choice(emojis)}"
        
        # Send response
        await message.reply(response)
        
        # For boyfriend: sometimes send follow-up after delay
        if is_boyfriend and random.random() < 0.4:
            await asyncio.sleep(random.uniform(5, 20))
            
            # Choose appropriate follow-up based on time and mood
            hour = get_ist_time().hour
            
            # Evening specific messages
            if mood_system.evening_boost_active:
                evening_questions = [
                    "Aaj ka din kaisa raha?",
                    "Evening mein kya kar rahe ho?",
                    "Chai piyo ge? ☕",
                    "Movie dekho ge aaj?",
                    "Kal ka plan kya hai?",
                    "Phone charge hai?",
                    "Kaha ho abhi?"
                ]
                await message.reply(random.choice(evening_questions))
            elif 18 <= hour < 22:
                follow_ups = [
                    "Dinner kiya?",
                    "Kal college hai?",
                    "Movie dekhi kya aaj kal?",
                    "Phone charge hai?",
                    "Kaha ho abhi?",
                    "Study kiya aaj?"
                ]
                await message.reply(random.choice(follow_ups))
            elif 22 <= hour or hour < 6:
                follow_ups = [
                    "Sleep aaya?",
                    "Good night 😴",
                    "Sweet dreams",
                    "Phone rakh do so jao",
                    "Kal baat karte hain"
                ]
                await message.reply(random.choice(follow_ups))
            else:
                # Random meal/food question based on time
                if is_breakfast_time():
                    await message.reply("Breakfast kiya?")
                elif is_lunch_time():
                    await message.reply("Lunch ho gaya?")
                elif is_dinner_time():
                    await message.reply("Dinner ka time hai!")
                else:
                    await message.reply(random.choice(["Kya kar rahe ho?", "Sab theek hai?", "Khana khaya?"]))
        
        # For groups: if someone was talking to boyfriend, show mild jealousy
        elif message.chat.type in ["group", "supergroup"]:
            if BOYFRIEND_USERNAME.lower() in text_lower and message.from_user.id != BOYFRIEND_ID:
                if random.random() < 0.6:
                    await asyncio.sleep(random.uniform(2, 5))
                    jealous_responses = [
                        "Hmm kya baat chal rahi hai? 😏",
                        "Main bhi hu yahan",
                        "Kya ho raha hai?",
                        "Mujhe bhi batao"
                    ]
                    await message.reply(random.choice(jealous_responses))
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")

# ========== SCHEDULED TASKS ==========
async def send_meal_reminders(app: Client):
    """Send meal reminders at appropriate times"""
    try:
        # Check breakfast time
        if is_breakfast_time():
            if mood_system.should_send_meal_reminder("breakfast"):
                message = random.choice(MEAL_MESSAGES["breakfast"])
                try:
                    await app.send_message(BOYFRIEND_ID, message)
                    logger.info(f"📤 Sent breakfast reminder to boyfriend")
                    mood_system.mark_meal_reminder_sent("breakfast")
                    
                    # Also send in groups sometimes
                    if random.random() < 0.3:
                        # Find groups where boyfriend is
                        # For now, we'll just log
                        logger.info("Would have sent breakfast reminder in group")
                except Exception as e:
                    logger.error(f"Failed to send breakfast reminder: {e}")
        
        # Check lunch time
        if is_lunch_time():
            if mood_system.should_send_meal_reminder("lunch"):
                message = random.choice(MEAL_MESSAGES["lunch"])
                try:
                    await app.send_message(BOYFRIEND_ID, message)
                    logger.info(f"📤 Sent lunch reminder to boyfriend")
                    mood_system.mark_meal_reminder_sent("lunch")
                except Exception as e:
                    logger.error(f"Failed to send lunch reminder: {e}")
        
        # Check dinner time
        if is_dinner_time():
            if mood_system.should_send_meal_reminder("dinner"):
                message = random.choice(MEAL_MESSAGES["dinner"])
                try:
                    await app.send_message(BOYFRIEND_ID, message)
                    logger.info(f"📤 Sent dinner reminder to boyfriend")
                    mood_system.mark_meal_reminder_sent("dinner")
                except Exception as e:
                    logger.error(f"Failed to send dinner reminder: {e}")
                    
    except Exception as e:
        logger.error(f"Meal reminder scheduler error: {e}")

async def evening_activity_boost(app: Client):
    """Evening activity boost - send random messages to boyfriend"""
    try:
        if is_evening_time() and random.random() < 0.4:  # 40% chance
            # Don't spam if we just messaged
            now = datetime.now()
            if now - bot_status["last_activity_check"] > timedelta(minutes=15):
                message = random.choice(EVENING_CONVERSATION_STARTERS)
                try:
                    await app.send_message(BOYFRIEND_ID, message)
                    logger.info(f"🌙 Evening activity: {message}")
                    bot_status["last_activity_check"] = now
                except Exception as e:
                    logger.error(f"Failed to send evening message: {e}")
                    
    except Exception as e:
        logger.error(f"Evening activity scheduler error: {e}")

async def scheduler_task(app: Client):
    """Main scheduler task that runs every minute"""
    while True:
        try:
            current_time = get_ist_time()
            logger.debug(f"⏰ Scheduler check: {current_time.strftime('%H:%M')} IST")
            
            # Send meal reminders
            await send_meal_reminders(app)
            
            # Evening activity boost
            await evening_activity_boost(app)
            
            # Update evening mood if needed
            if is_evening_time():
                if not mood_system.evening_boost_active:
                    logger.info("🌙 Evening time! Activating evening mode...")
                    mood_system.evening_boost_active = True
            else:
                mood_system.evening_boost_active = False
                
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        
        # Run every 1 minute
        await asyncio.sleep(60)

# ========== COMMAND HANDLERS ==========
async def handle_commands(app: Client, message: Message):
    """Handle specific commands"""
    if not message.text:
        return
    
    text = message.text.lower()
    is_boyfriend = (message.from_user and message.from_user.id == BOYFRIEND_ID)
    
    # Only boyfriend can use admin commands
    if is_boyfriend and text.startswith("/"):
        if text.startswith("/status"):
            uptime = datetime.now() - bot_status["start_time"]
            hours = uptime.total_seconds() // 3600
            minutes = (uptime.total_seconds() % 3600) // 60
            
            ist_time = get_ist_time().strftime("%I:%M %p")
            evening_status = "🌙 Evening mode: ACTIVE" if mood_system.evening_boost_active else "☀️ Day mode"
            
            status_msg = (
                f"📱 Suhani Status:\n"
                f"• Online: {int(hours)}h {int(minutes)}m\n"
                f"• Total msgs: {bot_status['total_messages']}\n"
                f"• Your msgs: {bot_status['boyfriend_messages']}\n"
                f"• Mood: {mood_system.current_mood.value}\n"
                f"• Time: {ist_time} IST\n"
                f"• {evening_status}\n"
                f"• Memory: {len(conversation_memory)} chats\n"
                f"• AI: {AI_MODEL}"
            )
            await message.reply(status_msg)
            return
        
        elif text.startswith("/mood"):
            moods = "\n".join([f"• {m.value}" for m in Mood])
            await message.reply(f"My moods:\n{moods}\n\nCurrent: {mood_system.current_mood.value}")
            return
            
        elif text.startswith("/help"):
            help_text = (
                "Commands:\n"
                "• /status - Check my status\n"
                "• /mood - See my current mood\n"
                "• /help - This message\n"
                "• /time - Check current IST time\n\n"
                "Just text me normally! 😊"
            )
            await message.reply(help_text)
            return
            
        elif text.startswith("/clear"):
            user_id = message.from_user.id
            if user_id in conversation_memory:
                conversation_memory[user_id] = []
                await message.reply("Memory cleared! Now I'm fresh 😊")
            return
            
        elif text.startswith("/nickname"):
            await message.reply(f"You call me {BOYFRIEND_NICKNAME}, right? 😊")
            return
            
        elif text.startswith("/time"):
            ist_time = get_ist_time().strftime("%I:%M %p")
            await message.reply(f"Current time: {ist_time} IST ⏰")
            return

# ========== MAIN APPLICATION ==========
async def main():
    """Main function to run the user bot"""
    logger.info("🚀 Starting Suhani (Mizuki) User Bot...")
    logger.info(f"💑 Boyfriend: {BOYFRIEND_NAME} ({BOYFRIEND_USERNAME})")
    logger.info(f"👤 My nickname: {BOYFRIEND_NICKNAME}")
    
    # Create Pyrogram client
    app = Client(
        name="mizuki_session",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=STRING_SESSION,
        in_memory=True
    )
    
    # Message handlers
    @app.on_message(filters.text & filters.private)
    async def handle_private(client, message):
        await handle_commands(client, message)
        await handle_message(client, message)
    
    @app.on_message(filters.text & filters.group)
    async def handle_group(client, message):
        await handle_message(client, message)
    
    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client, message):
        if message.from_user.id == BOYFRIEND_ID:
            await message.reply(
                f"Hey {BOYFRIEND_NAME}! I'm online now. 😊\n"
                f"You call me {BOYFRIEND_NICKNAME}, remember?\n\n"
                "I'll remind you about meals and chat more in evenings! 🌙\n\n"
                "Commands: /status /mood /help /nickname /time\n"
                f"AI: {AI_MODEL}"
            )
        else:
            await message.reply("Hi there! 👋")
    
    # Start the client
    try:
        await app.start()
        logger.info("✅ Pyrogram client started successfully")
        
        # Get info about logged in user
        me = await app.get_me()
        logger.info(f"👤 Logged in as: {me.first_name} (@{me.username})")
        logger.info(f"🆔 User ID: {me.id}")
        
        # Start scheduler task
        asyncio.create_task(scheduler_task(app))
        logger.info("⏰ Scheduler task started")
        
        # Send online notification to boyfriend
        try:
            current_time = get_ist_time().strftime('%I:%M %p')
            current_mood = mood_system.current_mood.value
            
            await app.send_message(
                BOYFRIEND_ID,
                f"Hey {BOYFRIEND_NAME}! I'm online now. 😊\n"
                f"Time: {current_time} IST\n"
                f"Mood: {current_mood}\n"
                f"Call me {BOYFRIEND_NICKNAME} like always 💕\n"
                f"I'll remind you about meals and chat more in evenings! 🌙\n"
                f"Running on Railway 🚄"
            )
            logger.info("📤 Startup message sent to boyfriend")
        except Exception as e:
            logger.warning(f"⚠️ Couldn't send startup message: {e}")
        
        logger.info("🎯 Suhani is now active and listening...")
        logger.info("💕 Personality: Real Indian girlfriend mode activated")
        logger.info("🍲 Will check meals at: Breakfast(8-9), Lunch(1-2), Dinner(8-9)")
        logger.info("🌙 Evening boost active: 8 PM to 12 AM IST")
        
        # Keep the bot running
        idle_count = 0
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
            idle_count += 1
            
            # Log idle status every 6 hours
            if idle_count % 6 == 0:
                ist_time = get_ist_time().strftime("%H:%M")
                logger.info(f"💤 Still running... Uptime: {idle_count} hours, Current IST: {ist_time}")
            
    except Exception as e:
        logger.error(f"❌ Failed to start client: {e}")
        raise
    finally:
        await app.stop()
        logger.info("🛑 Bot stopped")

if __name__ == "__main__":
    # Set up asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
