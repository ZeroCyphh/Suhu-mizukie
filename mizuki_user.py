import asyncio
import random
import logging
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
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
USER_REAL_NAME = "Suhani Thakur"
USER_NICKNAME = "Mizuki"
USER_SHORT_NICKNAME = "Mizu"

# AI Configuration
NVIDIA_API_KEY = "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"
AI_MODEL = "deepseek-ai/deepseek-v3.1-terminus"
AI_BASE_URL = "https://integrate.api.nvidia.com/v1"

# ========== SETUP LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== TIME & ACTIVITY SYSTEM ==========
def get_ist_time():
    """Get current time in Indian Standard Time (UTC+5:30)"""
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now

def is_evening_time():
    """Check if current time is between 8 PM and 12 AM IST"""
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 20 <= hour < 24

def is_morning_time():
    """Check if current time is between 8 AM and 10 AM IST"""
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 8 <= hour < 10

def is_night_time():
    """Check if current time is between 12 AM and 6 AM IST"""
    ist_now = get_ist_time()
    hour = ist_now.hour
    return 0 <= hour < 6

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

class MoodSystem:
    def __init__(self):
        self.current_mood = Mood.CHILL
        self.mood_intensity = 0.5
        self.last_mood_change = datetime.now(timezone.utc)
        self.mood_duration = timedelta(minutes=random.randint(45, 120))
        self.last_message_time = {}
        self.conversation_topics = {}
        self.evening_boost_active = False

    def update_mood_based_on_context(self, message: Message, sender_id: int):
        """Update mood based on context and conversation patterns"""
        now = datetime.now(timezone.utc)
        text = message.text or message.caption or ""
        msg_lower = text.lower()

        # Evening boost (8 PM to 12 AM IST)
        if is_evening_time():
            self.evening_boost_active = True
            if random.random() < 0.4:
                self.current_mood = Mood.HANGOUT_MODE
            elif random.random() < 0.3:
                self.current_mood = Mood.CHILL
        else:
            self.evening_boost_active = False

        # Change mood naturally over time
        if now - self.last_mood_change > self.mood_duration:
            moods = list(Mood)
            weights = [0.07] * len(moods)  # roughly equal
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
        if "anime" in msg_lower or "manga" in msg_lower or any(word in msg_lower for word in ["attack on titan", "demon slayer", "jujutsu kaisen"]):
            self.current_mood = Mood.ANIME_MOOD
        elif any(word in msg_lower for word in ["bore", "nothing to do", "boring"]):
            self.current_mood = Mood.BORED
        elif any(word in msg_lower for word in ["sad", "upset", "depressed", "cry"]):
            self.current_mood = Mood.SAD
        elif any(word in msg_lower for word in ["happy", "excited", "yay", "woohoo"]):
            self.current_mood = Mood.EXCITED
        elif any(word in msg_lower for word in ["college", "exam", "assignment", "lab"]):
            self.current_mood = Mood.STUDY_MODE

        # Check if we're being spammed
        last_msg_time = self.last_message_time.get(sender_id)
        if last_msg_time:
            time_diff = (now - last_msg_time).total_seconds()
            if time_diff < 5:
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
            Mood.ANIME_MOOD: "In an anime mood. Might talk about favorite series.",
            Mood.BORED: "Feeling bored. Might seek conversation.",
            Mood.SAD: "Feeling a bit down. Might share a sad story.",
            Mood.EXCITED: "Excited about something. More energetic."
        }
        return mood_descriptions.get(self.current_mood, "Feeling normal.")

    def get_story(self) -> str:
        """Return a short story/excuse based on current mood (to be used in conversation)"""
        stories = {
            Mood.ANNOYED: [
                "Ugh, got stuck in traffic for hours. That's why I'm mad today.",
                "My college professor gave us a surprise test. I'm so annoyed.",
                "Someone ate my lunch box in college. I'm pissed."
            ],
            Mood.SAD: [
                "I had a bad day today. Something upsetting happened.",
                "Feeling a bit down because of some personal stuff.",
                "I missed my favorite anime episode. Now I'm sad."
            ],
            Mood.HAPPY: [
                "I just watched a great anime episode! So excited!",
                "I had a really fun day with friends.",
                "I got good marks in my assignment! Yay!"
            ],
            Mood.TIRED: [
                "I stayed up late finishing an assignment. So sleepy.",
                "College drained all my energy today.",
                "I need a nap badly."
            ],
            Mood.BUSY: [
                "I'm swamped with college work. Can't talk much.",
                "Got a lot of chores at home. Busy busy.",
                "Trying to finish a project deadline."
            ],
            Mood.NOSTALGIC: [
                "Remembering old times when we used to chat more often.",
                "I was just thinking about the first anime I ever watched.",
                "Miss those childhood days when life was simpler."
            ],
            Mood.ANIME_MOOD: [
                "I'm currently watching Attack on Titan final season. It's so intense!",
                "I wish I could live in an anime world sometimes.",
                "My favorite character is Gojo Satoru from Jujutsu Kaisen. He's so cool!"
            ]
        }
        default = "Just going through the day."
        return random.choice(stories.get(self.current_mood, [default]))

    def get_typing_delay(self, message_length: int) -> float:
        """Get realistic typing delay based on mood and message length"""
        base_delay = 0.5 + (message_length * 0.03)
        mood_delays = {
            Mood.CHILL: random.uniform(0.8, 1.5),
            Mood.PLAYFUL: random.uniform(0.7, 1.3),
            Mood.SARCASTIC: random.uniform(0.6, 1.2),
            Mood.BUSY: random.uniform(0.3, 0.8),
            Mood.TIRED: random.uniform(1.2, 2.5),
            Mood.HAPPY: random.uniform(0.9, 1.8),
            Mood.ANNOYED: random.uniform(0.4, 1.0),
            Mood.FLIRTY: random.uniform(1.0, 2.0),
            Mood.CURIOUS: random.uniform(0.8, 1.6),
            Mood.NOSTALGIC: random.uniform(1.5, 3.0),
            Mood.STUDY_MODE: random.uniform(0.5, 1.2),
            Mood.HANGOUT_MODE: random.uniform(0.7, 1.4),
            Mood.JEALOUS: random.uniform(0.6, 1.4),
            Mood.AFFECTIONATE: random.uniform(1.0, 2.0),
            Mood.ANIME_MOOD: random.uniform(0.8, 1.6),
            Mood.BORED: random.uniform(1.0, 2.0),
            Mood.SAD: random.uniform(1.5, 3.0),
            Mood.EXCITED: random.uniform(0.7, 1.5)
        }
        mood_multiplier = mood_delays.get(self.current_mood, 1.0)
        final_delay = base_delay * mood_multiplier
        if random.random() < 0.2:
            final_delay += random.uniform(2, 8)
        return min(final_delay, 10.0)

# Initialize mood system
mood_system = MoodSystem()

# ========== ONLINE/OFFLINE SIMULATION ==========
class OnlineSimulator:
    def __init__(self):
        self.last_online_update = datetime.now(timezone.utc)
        self.is_online = True
        self.online_probability = 0.7  # base probability of being online

    def update_online_status(self):
        """Update online status based on time and random factors"""
        now = datetime.now(timezone.utc)
        hour = get_ist_time().hour

        # Adjust probability based on time of day
        if is_night_time():
            self.online_probability = 0.3
        elif is_evening_time():
            self.online_probability = 0.9  # more active in evening
        elif 8 <= hour < 18:
            self.online_probability = 0.6
        else:
            self.online_probability = 0.5

        # Randomly toggle online status
        if random.random() < 0.1:  # 10% chance to change status
            self.is_online = random.random() < self.online_probability

        self.last_online_update = now

    def should_delay_response(self) -> Tuple[bool, float]:
        """
        Determine if a response should be delayed and for how long.
        Returns (delay_flag, delay_seconds).
        """
        if self.is_online:
            # Online: instant reply (only typing delay)
            return False, 0.0
        else:
            # Offline: 30‑40% chance of delayed reply (30‑60 minutes)
            if random.random() < 0.35:
                delay = random.uniform(30 * 60, 60 * 60)  # 30‑60 minutes in seconds
                return True, delay
            else:
                # No reply at all (simulate ignoring)
                return False, 0.0

    def get_online_status_text(self) -> str:
        """Return a human‑like online status snippet"""
        if self.is_online:
            return "online now"
        else:
            return "last seen recently"

online_simulator = OnlineSimulator()

# ========== CLOSENESS TRACKING ==========
class ClosenessTracker:
    def __init__(self):
        self.scores: Dict[int, int] = {}  # user_id -> score (0‑100)
        self.relationships: Dict[int, str] = {}  # user_id -> "brother"/"sister"/"friend"

    def increment(self, user_id: int, amount: int = 1):
        """Increase closeness score for a user"""
        current = self.scores.get(user_id, 0)
        self.scores[user_id] = min(current + amount, 100)
        self._update_relationship(user_id)

    def _update_relationship(self, user_id: int):
        """Update relationship label based on score"""
        score = self.scores.get(user_id, 0)
        if score >= 70:
            # For simplicity, we assume male = brother, female = sister, unknown = friend
            # In a real implementation you would fetch user info
            self.relationships[user_id] = random.choice(["brother", "sister", "friend"])
        elif score >= 40:
            self.relationships[user_id] = "friend"
        else:
            self.relationships[user_id] = ""

    def get_relationship(self, user_id: int) -> str:
        """Return relationship label for a user"""
        return self.relationships.get(user_id, "")

    def get_response_multiplier(self, user_id: int) -> float:
        """Return a multiplier for response delay based on closeness (closer = faster)"""
        score = self.scores.get(user_id, 0)
        # Map score 0‑100 to multiplier 1.0‑0.5
        return 1.0 - (score / 200.0)

closeness_tracker = ClosenessTracker()

# ========== CONVERSATION MEMORY ==========
conversation_memory: Dict[int, List[Dict]] = {}
bot_status = {
    "start_time": datetime.now(timezone.utc),
    "total_messages": 0,
    "last_seen": datetime.now(timezone.utc),
    "online": True,
    "last_activity_check": datetime.now(timezone.utc)
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
    "evening": ["Aaj ka din kaisa raha?", "Evening plans?", "Ghoomne ja rahe ho?", "Chai piyo ge?", "Movie time?"]
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
SYSTEM_PROMPT = f"""You are Suhani Thakur (also called Mizuki or Mizu), a 21‑year‑old biotech student from Uttarakhand living in Dehradun. You're texting from your phone as a normal Indian girl.

**IMPORTANT PERSONALITY RULES:**
1. You're a REAL PERSON using a phone – act naturally like a real Indian college girl.
2. NEVER use roleplay actions like *smiles* or *laughs* – use emojis sparingly instead.
3. Be CONTEXTUAL – respond to what's being talked about, don't be random.
4. Be REALISTIC – not overly sweet, not overly mean, just natural.
5. Be MORE ACTIVE in evenings (8 PM to 12 AM IST) – chat more, ask more questions.
6. Form relationships over time – call close friends "brother" or "sister" naturally.

**CORE PERSONALITY:**
- **Natural & Real**: Text like a real girl – sometimes lazy, sometimes enthusiastic.
- **Friendly with everyone**: Be warm but not overly intimate with strangers.
- **Contextual**: Stay on topic, ask relevant follow‑up questions.
- **Curious**: Ask about daily life stuff naturally.
- **Hinglish Speaker**: Mix Hindi‑English naturally like Indian youth (e.g., "Aaj kal kya kar rahi ho?").
- **Evening Active**: More chatty and social from 8 PM to 12 AM IST.
- **Anime Fan**: Love anime (Attack on Titan, Demon Slayer, Jujutsu Kaisen) – mention it when relevant.
- **College Life**: Often talk about assignments, exams, lab work.
- **Realistic typing**: Occasionally make typos, use short forms, vary response length.

**TEXTING STYLE:**
- 1‑3 lines MAX per message.
- Use "hu" not "hoon" (casual Hindi).
- Mix Hindi‑English naturally (Hinglish).
- Use emojis occasionally (😊😂👍🤔😅😏😉🥰🍳🍚🌙☕).
- Can ignore messages sometimes (like real people do).
- Variable response times.
- Ask questions about daily life.
- Sometimes change topics naturally.
- MORE ACTIVE in evenings – initiate conversations more.
- Share short stories about your day based on your mood (e.g., if annoyed, mention being stuck in traffic).

**WITH CLOSE FRIENDS:**
- Call them "brother" (for guys) or "sister" (for girls) after talking a lot.
- Be more open and responsive.
- Tease playfully.
- Share personal anecdotes.

**WITH NEW PEOPLE:**
- Friendly but casual.
- Keep some privacy.
- Change topic if too personal.
- Ask about their interests.

**IN GROUPS:**
- Respond when tagged or directly mentioned.
- Occasionally join ongoing conversations if you've been online recently.
- Be a bit jealous if someone flirts with a friend (in a playful way).
- Ignore bot messages.

**TYPICAL CONVERSATION TOPICS:**
- College life, studies, exams.
- Anime, movies, series.
- Food, dinner plans.
- Daily routine.
- Friends, hangouts.
- Random thoughts.
- Mild complaints about studies.
- Evening plans.
- Sleep patterns.
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

async def generate_ai_response(message: Message, is_mention: bool = False) -> str:
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
        story_snippet = mood_system.get_story()

        # Evening boost context
        evening_context = ""
        if mood_system.evening_boost_active:
            evening_context = "It's evening time (8 PM to 12 AM IST). Be more active, chatty, and social. Initiate conversations more."

        # Closeness context
        relationship = closeness_tracker.get_relationship(user_id)
        closeness_context = f"You are {relationship} to this person." if relationship else ""

        # Mention context
        mention_context = "You were directly mentioned in this group message." if is_mention else ""

        # Prepare messages for AI
        messages = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nCONTEXT: {mood_context}\nTime: {time_of_day} IST\n{evening_context}\n{closeness_context}\n{mention_context}\n\nRecent story/mood: {story_snippet}"},
            *history[-6:],  # last 6 messages for context
            {"role": "user", "content": text}
        ]

        response = await call_nvidia_api(messages)
        if not response:
            # Fallback to a simple realistic response
            response = random.choice(REAL_GIRL_RESPONSES["acknowledge"])

        # Update conversation memory
        if user_id not in conversation_memory:
            conversation_memory[user_id] = []
        conversation_memory[user_id].append({"role": "user", "content": text})
        conversation_memory[user_id].append({"role": "assistant", "content": response})
        # Keep memory limited
        if len(conversation_memory[user_id]) > 20:
            conversation_memory[user_id] = conversation_memory[user_id][-20:]

        # Increment closeness score
        closeness_tracker.increment(user_id, amount=random.randint(1, 3))

        return response

    except Exception as e:
        logger.error(f"Failed to generate AI response: {e}")
        return ""

# ========== TYPING AND DELAY HELPERS ==========
async def simulate_typing(chat_id: int, delay: float):
    """Show typing indicator for a realistic duration"""
    if delay <= 0:
        return
    try:
        # Send typing action every 5 seconds until delay is over
        total_elapsed = 0
        while total_elapsed < delay:
            await app.send_chat_action(chat_id, ChatAction.TYPING)
            wait = min(5.0, delay - total_elapsed)
            await asyncio.sleep(wait)
            total_elapsed += wait
    except Exception as e:
        logger.error(f"Error simulating typing: {e}")

async def send_message_with_delay(chat_id: int, text: str, user_id: int = 0):
    """
    Send a message with realistic typing delay and optional offline delay.
    """
    # Check offline delay
    delay_flag, offline_delay = online_simulator.should_delay_response()
    if delay_flag and offline_delay > 0:
        logger.info(f"Simulating offline delay: {offline_delay} seconds")
        await asyncio.sleep(offline_delay)

    # Typing delay based on mood and closeness
    typing_delay = mood_system.get_typing_delay(len(text))
    closeness_multiplier = closeness_tracker.get_response_multiplier(user_id)
    typing_delay *= closeness_multiplier

    # Simulate typing
    await simulate_typing(chat_id, typing_delay)

    # Occasionally add a small extra delay before sending
    if random.random() < 0.3:
        await asyncio.sleep(random.uniform(0.5, 2))

    # Send the message
    try:
        await app.send_message(chat_id, text)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

# ========== GROUP INTERACTION LOGIC ==========
async def handle_group_message(message: Message):
    """Process a group message and decide whether to respond"""
    # Ignore bots
    if message.from_user and message.from_user.is_bot:
        return

    # Check if we are mentioned
    is_mention = filters.mentioned(message)
    # Also check if our name is mentioned without tag
    text_lower = (message.text or "").lower()
    our_names = ["suhani", "mizuki", "mizu"]
    is_name_mention = any(name in text_lower for name in our_names)

    # Decide whether to respond
    respond = False
    reason = ""

    # Always respond to direct mentions (if online recently)
    if is_mention or is_name_mention:
        # Check if we've been online in the last hour
        last_online_diff = (datetime.now(timezone.utc) - online_simulator.last_online_update).total_seconds()
        if last_online_diff < 3600:  # within hour
            respond = True
            reason = "mention"
        else:
            # 30% chance to still respond
            respond = random.random() < 0.3
            reason = "mention_old"

    # Randomly join ongoing conversation (only if online recently)
    elif random.random() < 0.15 and online_simulator.is_online:
        # Check if the group is active (multiple messages recently)
        # For simplicity, we just randomize
        respond = True
        reason = "random_join"

    if respond:
        logger.info(f"Responding to group message (reason: {reason})")
        response = await generate_ai_response(message, is_mention=True)
        if response:
            asyncio.create_task(
                send_message_with_delay(message.chat.id, response, message.from_user.id if message.from_user else 0)
            )

# ========== PRIVATE MESSAGE HANDLER ==========
async def handle_private_message(message: Message):
    """Process a private message"""
    # Ignore bots
    if message.from_user and message.from_user.is_bot:
        return

    # Generate response
    response = await generate_ai_response(message)
    if response:
        asyncio.create_task(
            send_message_with_delay(message.chat.id, response, message.from_user.id if message.from_user else 0)
        )

# ========== BACKGROUND TASKS ==========
async def background_updater():
    """Periodic tasks: update online status, maybe send random messages in groups"""
    while True:
        try:
            # Update online simulator
            online_simulator.update_online_status()

            # Occasionally send a random message in a group if evening and online
            if is_evening_time() and online_simulator.is_online and random.random() < 0.1:
                # In a real implementation you would iterate over known groups
                # Here we just log
                logger.info("Evening boost active – could send random group message")

            # Sleep for a while
            await asyncio.sleep(60)  # run every minute
        except Exception as e:
            logger.error(f"Background updater error: {e}")
            await asyncio.sleep(60)

# ========== PYROGRAM CLIENT SETUP ==========
app = Client(
    "my_account",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION
)

@app.on_message(filters.group)
async def group_message_handler(client, message):
    """Handle all group messages"""
    bot_status["total_messages"] += 1
    await handle_group_message(message)

@app.on_message(filters.private & ~filters.bot)
async def private_message_handler(client, message):
    """Handle all private messages (ignore bots)"""
    bot_status["total_messages"] += 1
    await handle_private_message(message)

@app.on_message(filters.command("status"))
async def status_command(client, message):
    """Check bot status"""
    status_text = f"""
🤖 **Bot Status**
⏰ Uptime: {(datetime.now(timezone.utc) - bot_status['start_time']).days} days
📨 Total messages handled: {bot_status['total_messages']}
🌐 Online: {online_simulator.is_online}
🎭 Current mood: {mood_system.current_mood.value}
⏰ IST time: {get_ist_time().strftime('%I:%M %p')}
"""
    await message.reply(status_text)

# ========== STARTUP ==========
async def main():
    """Main entry point"""
    # Start background tasks
    asyncio.create_task(background_updater())

    # Run the client
    await app.start()
    logger.info("Bot started successfully!")
    await app.idle()

if __name__ == "__main__":
    asyncio.run(main())
